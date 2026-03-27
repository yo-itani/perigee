"""Integration tests for system router endpoints."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from main import app


@pytest.mark.integration
class TestGetSystemStatus:
    """Tests for GET /system/status."""

    async def test_returns_status(self) -> None:
        """GET /system/status returns is_setup_complete field."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/system/status")

        assert response.status_code == 200
        data = response.json()
        assert "is_setup_complete" in data
        assert isinstance(data["is_setup_complete"], bool)


@pytest.mark.integration
class TestSetupFirstUser:
    """Tests for POST /system/setup."""

    async def test_setup_creates_admin_user(self) -> None:
        """POST /system/setup creates the first admin user (201)."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/system/setup",
                json={"name": "Admin", "email": "admin@example.com"},
            )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Admin"
        assert data["email"] == "admin@example.com"
        assert data["role"] == "admin"
        assert data["is_active"] is True

    async def test_setup_rejects_when_already_complete(self) -> None:
        """POST /system/setup returns 409 when setup is already complete."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # First call should succeed
            first = await client.post(
                "/system/setup",
                json={"name": "Admin", "email": "first@example.com"},
            )
            assert first.status_code == 201

            # Second call should be rejected
            second = await client.post(
                "/system/setup",
                json={"name": "Another", "email": "second@example.com"},
            )

        assert second.status_code == 409

    async def test_setup_rejects_invalid_email(self) -> None:
        """POST /system/setup returns 422 for invalid email."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/system/setup",
                json={"name": "Admin", "email": "not-an-email"},
            )

        assert response.status_code == 422
