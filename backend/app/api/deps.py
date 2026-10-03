"""Authentication dependencies, role-based authorization, and security filters."""

import uuid
from collections.abc import AsyncGenerator

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.logging import logger
from app.core.security import decode_token
from app.db.session import AsyncSessionLocal
from app.models.audit_log import AuditLog
from app.models.user import User

security_scheme = HTTPBearer(auto_error=True)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Provides an asynchronous database session per request."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Extracts, validates, and retrieves the authenticated User from the JWT Bearer token."""
    token = credentials.credentials
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_token(token)
        token_type = payload.get("type")
        user_id_str = payload.get("sub")

        if token_type != "access" or not user_id_str:
            raise credentials_exception

        user_id = uuid.UUID(user_id_str)
    except (jwt.PyJWTError, ValueError) as exc:
        logger.warning(f"JWT validation failed: {exc!s}")
        raise credentials_exception from exc

    stmt = (
        select(User)
        .options(
            selectinload(User.profile),
            selectinload(User.preferences),
            selectinload(User.emergency_contacts),
        )
        .where(User.id == user_id)
    )
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user account")

    return user


def require_role(*allowed_roles: str | list[str]):
    """Enforces role-based access control (RBAC)."""
    flattened_roles: list[str] = []
    for r in allowed_roles:
        if isinstance(r, (list, tuple)):
            flattened_roles.extend(r)
        else:
            flattened_roles.append(r)

    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in flattened_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation not permitted. Required role: {', '.join(flattened_roles)}",
            )
        return current_user

    return role_checker


def sanitize_audit_details(details: dict | None) -> dict | None:
    """Sanitizes sensitive fields, credentials, and high-precision coordinates for audit records."""
    if not details:
        return details
    sanitized: dict = {}
    for k, v in details.items():
        k_lower = str(k).lower()
        if any(secret_kw in k_lower for secret_kw in ("password", "secret", "token", "api_key", "credential")):
            sanitized[k] = "[REDACTED]"
        elif k_lower in ("lat", "latitude", "lon", "longitude", "lng") and isinstance(v, (int, float)):
            sanitized[k] = round(float(v), 2)
        elif isinstance(v, dict):
            sanitized[k] = sanitize_audit_details(v)
        elif isinstance(v, list):
            sanitized[k] = [
                sanitize_audit_details(item) if isinstance(item, dict) else item
                for item in v
            ]
        elif isinstance(v, str):
            val = v
            if "bearer " in val.lower():
                import re

                val = re.sub(r"bearer\s+[a-zA-Z0-9_\-\.]+", "Bearer [REDACTED]", val, flags=re.IGNORECASE)
            sanitized[k] = val
        else:
            sanitized[k] = v
    return sanitized


async def log_audit_event(
    db: AsyncSession,
    action: str,
    user_id: uuid.UUID | None = None,
    request: Request | None = None,
    details: dict | None = None,
) -> None:
    """Records an audit log entry for authentication and sensitive clinical operations."""
    ip_address = None
    user_agent = None

    if request:
        client = request.client
        ip_address = client.host if client else None
        user_agent = request.headers.get("user-agent")

    clean_details = sanitize_audit_details(details)

    audit = AuditLog(
        user_id=user_id,
        action=action,
        ip_address=ip_address,
        user_agent=user_agent,
        details=clean_details,
    )
    db.add(audit)
    await db.commit()
