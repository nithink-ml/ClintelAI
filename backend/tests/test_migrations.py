"""Database migration test verifying schema and Alembic revision state."""

import pytest
from sqlalchemy import text

from app.db.session import engine


@pytest.mark.asyncio
async def test_database_tables_and_alembic_head():
    """Verifies that all Phase 1 tables exist and Alembic revision is applied."""
    async with engine.connect() as conn:
        # Check alembic version table
        version_res = await conn.execute(text("SELECT version_num FROM alembic_version;"))
        version = version_res.scalar()
        assert version == "7c8910d5e6f1"

        # Check required Phase 1, Phase 3 & Phase 4 tables exist
        tables_res = await conn.execute(
            text(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'public';"
            )
        )
        tables = {row[0] for row in tables_res.fetchall()}
        required_tables = {
            "users",
            "profiles",
            "user_preferences",
            "emergency_contacts",
            "audit_logs",
            "refresh_tokens",
            "facilities",
            "doctors",
            "doctor_affiliations",
            "health_alerts",
        }
        for tbl in required_tables:
            assert tbl in tables, f"Missing expected table {tbl} in database"

        # Check users table columns
        cols_res = await conn.execute(
            text(
                "SELECT column_name, data_type FROM information_schema.columns "
                "WHERE table_name = 'users';"
            )
        )
        user_cols = {row[0]: row[1] for row in cols_res.fetchall()}
        assert "id" in user_cols
        assert "email" in user_cols
        assert "hashed_password" in user_cols
        assert "role" in user_cols
        assert "is_active" in user_cols
        assert "is_verified" in user_cols
