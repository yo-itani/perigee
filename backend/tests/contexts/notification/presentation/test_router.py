"""Integration tests for notification-settings API endpoints.

These tests exercise the full HTTP layer (router -> use case -> repository)
using the real FastAPI app with httpx.AsyncClient.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from api.event_setup import create_event_dispatcher
from api.exception_handlers import register_exception_handlers
from api.register_routers import register_routers

pytestmark = pytest.mark.integration

_BASE_URL = "http://test"


def _create_test_app():
    """Create a FastAPI app wired with routers and exception handlers."""
    from fastapi import FastAPI

    app = FastAPI()
    app.state.event_dispatcher = create_event_dispatcher()
    register_exception_handlers(app)
    register_routers(app)
    return app


@pytest.fixture
def app():
    return _create_test_app()


@pytest.fixture
def user_id() -> str:
    return str(uuid.uuid4())


class TestGetNotificationSetting:
    """GET /notification-settings"""

    async def test_returns_default_when_no_setting_exists(
        self, app, user_id: str
    ) -> None:
        """An authenticated user with no persisted setting gets defaults."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            response = await client.get(
                "/notification-settings",
                headers={"X-User-Id": user_id},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == user_id
        assert data["reminder_minutes_before"] == 30
        assert data["is_enabled"] is True

    async def test_returns_401_without_auth_header(self, app) -> None:
        """Request without X-User-Id header returns 401."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            response = await client.get("/notification-settings")

        assert response.status_code == 401

    async def test_returns_401_with_invalid_user_id(self, app) -> None:
        """Request with non-UUID X-User-Id returns 401."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            response = await client.get(
                "/notification-settings",
                headers={"X-User-Id": "not-a-uuid"},
            )

        assert response.status_code == 401


class TestUpdateNotificationSetting:
    """PUT /notification-settings"""

    async def test_creates_setting_on_first_update(self, app, user_id: str) -> None:
        """First PUT creates the setting and returns the new values."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            response = await client.put(
                "/notification-settings",
                headers={"X-User-Id": user_id},
                json={"reminder_minutes_before": 60, "is_enabled": False},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == user_id
        assert data["reminder_minutes_before"] == 60
        assert data["is_enabled"] is False

    async def test_updates_existing_setting(self, app, user_id: str) -> None:
        """Second PUT updates the previously created setting."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            # Create initial setting
            await client.put(
                "/notification-settings",
                headers={"X-User-Id": user_id},
                json={"reminder_minutes_before": 60, "is_enabled": False},
            )
            # Update it
            response = await client.put(
                "/notification-settings",
                headers={"X-User-Id": user_id},
                json={"reminder_minutes_before": 15, "is_enabled": True},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["reminder_minutes_before"] == 15
        assert data["is_enabled"] is True

    async def test_get_returns_updated_value_after_put(self, app, user_id: str) -> None:
        """GET reflects the value saved by a preceding PUT."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            await client.put(
                "/notification-settings",
                headers={"X-User-Id": user_id},
                json={"reminder_minutes_before": 120, "is_enabled": False},
            )
            response = await client.get(
                "/notification-settings",
                headers={"X-User-Id": user_id},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["reminder_minutes_before"] == 120
        assert data["is_enabled"] is False

    async def test_returns_422_for_reminder_below_minimum(
        self, app, user_id: str
    ) -> None:
        """reminder_minutes_before < 5 triggers domain validation error."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            response = await client.put(
                "/notification-settings",
                headers={"X-User-Id": user_id},
                json={"reminder_minutes_before": 4, "is_enabled": True},
            )

        assert response.status_code == 422

    async def test_returns_422_for_reminder_above_maximum(
        self, app, user_id: str
    ) -> None:
        """reminder_minutes_before > 1440 triggers domain validation error."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            response = await client.put(
                "/notification-settings",
                headers={"X-User-Id": user_id},
                json={"reminder_minutes_before": 1441, "is_enabled": True},
            )

        assert response.status_code == 422

    async def test_returns_401_without_auth_header(self, app) -> None:
        """PUT without X-User-Id header returns 401."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            response = await client.put(
                "/notification-settings",
                json={"reminder_minutes_before": 30, "is_enabled": True},
            )

        assert response.status_code == 401

    async def test_boundary_min_reminder_accepted(self, app, user_id: str) -> None:
        """reminder_minutes_before = 5 (minimum) is accepted."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            response = await client.put(
                "/notification-settings",
                headers={"X-User-Id": user_id},
                json={"reminder_minutes_before": 5, "is_enabled": True},
            )

        assert response.status_code == 200
        assert response.json()["reminder_minutes_before"] == 5

    async def test_boundary_max_reminder_accepted(self, app, user_id: str) -> None:
        """reminder_minutes_before = 1440 (maximum) is accepted."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            response = await client.put(
                "/notification-settings",
                headers={"X-User-Id": user_id},
                json={"reminder_minutes_before": 1440, "is_enabled": True},
            )

        assert response.status_code == 200
        assert response.json()["reminder_minutes_before"] == 1440
