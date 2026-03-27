"""Integration tests for system router endpoints using real DB."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, text
from sqlalchemy.ext.asyncio import AsyncSession

from foundation.db.session import async_session_factory
from main import app
from shared.infrastructure.tables import UserTable

pytestmark = pytest.mark.integration


async def _cleanup(session: AsyncSession) -> None:
    """Remove test data from users and system_settings tables."""
    await session.execute(
        delete(UserTable).where(UserTable.email == "admin@example.com")
    )
    # Reset setup_completed_at to NULL so the singleton row is reusable.
    await session.execute(
        text("UPDATE system_settings SET setup_completed_at = NULL WHERE id = 1")
    )
    await session.commit()


class TestSetupFirstUserIntegration:
    """Integration tests for POST /system/setup against real MariaDB."""

    async def test_first_setup_succeeds_second_returns_409(self) -> None:
        """POST /system/setup succeeds on first call (201) and fails on second (409)."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Ensure clean state
            async with async_session_factory() as session:
                await _cleanup(session)

            # First call should succeed
            response1 = await client.post(
                "/system/setup",
                json={"name": "Admin", "email": "admin@example.com"},
            )
            assert response1.status_code == 201
            data = response1.json()
            assert data["name"] == "Admin"
            assert data["email"] == "admin@example.com"
            assert data["role"] == "admin"
            assert data["is_active"] is True

            # Second call should fail with 409
            response2 = await client.post(
                "/system/setup",
                json={"name": "Admin2", "email": "admin@example.com"},
            )
            assert response2.status_code == 409

        # Cleanup
        async with async_session_factory() as session:
            await _cleanup(session)
