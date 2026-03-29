"""FastAPI router for test-only endpoints (E2E testing).

This router is only registered when PERIGEE_ENABLE_TEST_ENDPOINTS=true.
All operations validate that the connected DB name starts with 'perigee_e2e'
as a safety guard against accidental execution on production/development databases.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import text

from foundation.db.session import engine

test_router = APIRouter(prefix="/test", tags=["Test"])

_E2E_DB_PREFIX = "perigee_e2e"


async def _get_current_db_name() -> str:
    """Get the current database name from the active connection."""
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT DATABASE()"))
        row = result.fetchone()
        if row is None or row[0] is None:
            return ""
        db_name: str = row[0]
        return db_name


def _validate_e2e_db(db_name: str) -> None:
    """Raise 404 if the database name does not start with the E2E prefix."""
    if not db_name.startswith(_E2E_DB_PREFIX):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Not Found",
        )


@test_router.post("/reset", status_code=status.HTTP_204_NO_CONTENT)
async def reset_database() -> None:
    """Reset the test database by truncating all tables.

    Safety guards:
    - Only available when PERIGEE_ENABLE_TEST_ENDPOINTS=true
    - Returns 404 if the connected DB name does not start with 'perigee_e2e'
    """
    db_name = await _get_current_db_name()
    _validate_e2e_db(db_name)

    async with engine.begin() as conn:
        # Get all table names
        result = await conn.execute(
            text(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = :db_name AND table_type = 'BASE TABLE'"
            ),
            {"db_name": db_name},
        )
        table_names = [row[0] for row in result.fetchall()]

        if table_names:
            await conn.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
            for table_name in table_names:
                # Use backtick quoting for table names (safe: from information_schema)
                await conn.execute(text(f"TRUNCATE TABLE `{table_name}`"))
            await conn.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
