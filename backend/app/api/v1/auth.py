"""Authentication and token management endpoints."""

import uuid
from datetime import UTC, datetime

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, log_audit_event
from app.core.config import settings
from app.core.logging import logger
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    verify_password,
)
from app.models.preference import UserPreference
from app.models.profile import Profile
from app.models.token import RefreshToken
from app.models.user import User
from app.schemas.token import RefreshTokenRequest, TokenResponse
from app.schemas.user import (
    UserDetailResponse,
    UserLoginRequest,
    UserRegisterRequest,
)

router = APIRouter()


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register New User Account",
    description="Creates a new patient or user account, profile, and initial preferences.",
)
async def register_user(
    payload: UserRegisterRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    # 1. Normalize and check email uniqueness
    normalized_email = payload.email.lower().strip()
    existing_stmt = select(User).where(User.email == normalized_email)
    existing_res = await db.execute(existing_stmt)
    if existing_res.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email address already exists.",
        )

    # 2. Hash password securely
    hashed_pwd = get_password_hash(payload.password)

    # 3. Create user entity
    new_user = User(
        email=normalized_email,
        hashed_password=hashed_pwd,
        role="user",
        is_active=True,
        is_verified=False,
    )
    db.add(new_user)
    await db.flush()  # Populates new_user.id

    # 4. Create default profile
    new_profile = Profile(
        user_id=new_user.id,
        full_name=payload.full_name.strip(),
    )
    db.add(new_profile)

    # 5. Create default preferences
    new_pref = UserPreference(
        user_id=new_user.id,
        preferred_language=payload.preferred_language,
        theme="system",
        emergency_alerts_enabled=True,
        location_sharing_enabled=False,
    )
    db.add(new_pref)

    # 6. Generate access and refresh tokens
    access_token = create_access_token(subject=str(new_user.id), role=new_user.role)
    refresh_token, expires_at = create_refresh_token(subject=str(new_user.id))

    # 7. Store refresh token for revocation and rotation tracking
    stored_token = RefreshToken(
        user_id=new_user.id,
        token=refresh_token,
        expires_at=expires_at,
        revoked=False,
    )
    db.add(stored_token)
    await db.commit()

    # 8. Record immutable audit log
    await log_audit_event(
        db=db,
        action="AUTH_REGISTER",
        user_id=new_user.id,
        request=request,
        details={"email": normalized_email, "language": payload.preferred_language},
    )

    logger.info(f"Registered new user account: {new_user.id} ({normalized_email})")

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Authenticate User",
    description="Verifies user credentials and issues short-lived access and refresh tokens.",
)
async def login_user(
    payload: UserLoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    normalized_email = payload.email.lower().strip()
    stmt = select(User).where(User.email == normalized_email)
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()

    if not user or not verify_password(payload.password, user.hashed_password):
        # Prevent timing attacks and user enumeration
        await log_audit_event(
            db=db,
            action="AUTH_LOGIN_FAILED",
            request=request,
            details={"email": normalized_email},
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated. Please contact support.",
        )

    # Issue tokens
    access_token = create_access_token(subject=str(user.id), role=user.role)
    refresh_token, expires_at = create_refresh_token(subject=str(user.id))

    # Save refresh token
    stored_token = RefreshToken(
        user_id=user.id,
        token=refresh_token,
        expires_at=expires_at,
        revoked=False,
    )
    db.add(stored_token)
    await db.commit()

    # Record login audit event
    await log_audit_event(
        db=db,
        action="AUTH_LOGIN_SUCCESS",
        user_id=user.id,
        request=request,
    )

    logger.info(f"User logged in successfully: {user.id}")

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Rotate Refresh Token",
    description="Rotates refresh tokens and issues a fresh short-lived access token.",
)
async def refresh_access_token(
    payload: RefreshTokenRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    unauthorized_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired refresh token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        token_payload = decode_token(payload.refresh_token)
        if token_payload.get("type") != "refresh":
            raise unauthorized_error
        user_id = uuid.UUID(token_payload.get("sub"))
    except (jwt.PyJWTError, ValueError) as exc:
        raise unauthorized_error from exc

    # Check token record in database
    stmt = select(RefreshToken).where(
        RefreshToken.token == payload.refresh_token,
        RefreshToken.user_id == user_id,
        RefreshToken.revoked.is_(False),
    )
    result = await db.execute(stmt)
    token_record = result.scalar_one_or_none()

    now_utc = datetime.now(UTC)
    if not token_record or token_record.expires_at < now_utc:
        raise unauthorized_error

    # Revoke old refresh token (strict token rotation)
    token_record.revoked = True

    # Check user active status
    user_stmt = select(User).where(User.id == user_id)
    user_res = await db.execute(user_stmt)
    user = user_res.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="User account is deactivated"
        )

    # Issue new token pair
    new_access_token = create_access_token(subject=str(user.id), role=user.role)
    new_refresh_token, new_expires_at = create_refresh_token(subject=str(user.id))

    new_token_record = RefreshToken(
        user_id=user.id,
        token=new_refresh_token,
        expires_at=new_expires_at,
        revoked=False,
    )
    db.add(new_token_record)
    await db.commit()

    await log_audit_event(
        db=db,
        action="AUTH_TOKEN_ROTATED",
        user_id=user.id,
        request=request,
    )

    return TokenResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post(
    "/logout",
    status_code=status.HTTP_200_OK,
    summary="Revoke User Session",
    description="Revokes the specified refresh token and closes active session.",
)
async def logout_user(
    payload: RefreshTokenRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(RefreshToken).where(
        RefreshToken.token == payload.refresh_token,
        RefreshToken.user_id == current_user.id,
    )
    res = await db.execute(stmt)
    token_record = res.scalar_one_or_none()

    if token_record:
        token_record.revoked = True
        await db.commit()

    await log_audit_event(
        db=db,
        action="AUTH_LOGOUT",
        user_id=current_user.id,
        request=request,
    )

    return {"detail": "Successfully logged out."}


@router.get(
    "/me",
    response_model=UserDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Current User Details",
    description="Returns current authenticated user identity with profile, preferences, and emergency contacts.",
)
async def get_me(
    current_user: User = Depends(get_current_user),
) -> UserDetailResponse:
    return UserDetailResponse.model_validate(current_user)
