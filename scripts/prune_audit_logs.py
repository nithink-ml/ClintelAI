"""Privacy & Data Retention Cleanup: Prunes outdated audit logs and purges expired refresh tokens."""

import asyncio
import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, func, select, update

from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.models.audit_log import AuditLog
from app.models.token import RefreshToken

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("clintelai.retention")


async def prune_retention_data(
    audit_retention_days: int = 90,
    security_audit_retention_days: int = 365,
    token_retention_days: int = 14,
):
    """Enforces data minimization and retention limits in accordance with healthcare privacy standards.

    1. Deletes general user access audit logs older than `audit_retention_days`.
    2. Deletes security/admin audit logs older than `security_audit_retention_days`.
    3. Purges revoked or expired refresh tokens older than `token_retention_days`.
    """
    now = datetime.now(UTC)
    audit_cutoff = now - timedelta(days=audit_retention_days)
    security_cutoff = now - timedelta(days=security_audit_retention_days)
    token_cutoff = now - timedelta(days=token_retention_days)

    logger.info("Starting ClintelAI Privacy & Data Retention Pruning...")
    logger.info(f"General Audit Retention Cutoff: {audit_cutoff.isoformat()}")
    logger.info(f"Security Audit Retention Cutoff: {security_cutoff.isoformat()}")
    logger.info(f"Token Retention Cutoff: {token_cutoff.isoformat()}")

    async with AsyncSessionLocal() as session:
        # 1. Prune general audit logs
        general_stmt = (
            delete(AuditLog)
            .where(AuditLog.created_at < audit_cutoff)
            .where(AuditLog.action.notin_(["ADMIN_ACTION", "SECURITY_ALERT", "RBAC_VIOLATION"]))
        )
        res_audit = await session.execute(general_stmt)
        pruned_audits = res_audit.rowcount or 0

        # 2. Prune old security logs past long-term retention
        sec_stmt = (
            delete(AuditLog)
            .where(AuditLog.created_at < security_cutoff)
            .where(AuditLog.action.in_(["ADMIN_ACTION", "SECURITY_ALERT", "RBAC_VIOLATION"]))
        )
        res_sec = await session.execute(sec_stmt)
        pruned_sec = res_sec.rowcount or 0

        # 3. Purge revoked or expired refresh tokens
        token_stmt = delete(RefreshToken).where(
            (RefreshToken.expires_at < token_cutoff) | (RefreshToken.is_revoked == True)
        )
        res_tokens = await session.execute(token_stmt)
        pruned_tokens = res_tokens.rowcount or 0

        await session.commit()

        # 4. Summary counts
        total_audits = (await session.execute(select(func.count(AuditLog.id)))).scalar() or 0
        total_tokens = (await session.execute(select(func.count(RefreshToken.id)))).scalar() or 0

        logger.info(f"Successfully pruned {pruned_audits} general audit logs.")
        logger.info(f"Successfully pruned {pruned_sec} expired security audit logs.")
        logger.info(f"Successfully purged {pruned_tokens} expired refresh tokens.")
        logger.info(f"Current remaining audit logs: {total_audits}, active tokens: {total_tokens}")


if __name__ == "__main__":
    asyncio.run(prune_retention_data())
