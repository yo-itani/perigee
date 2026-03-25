"""Integration tests for Preparation context API endpoints.

These tests exercise the full HTTP layer (router -> DI -> use case -> repository -> DB)
using the real FastAPI app with httpx.AsyncClient.  No DI overrides are used.
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


class TestCreateScheduleGroupAuth:
    """POST /schedule-groups -- authentication checks."""

    async def test_returns_401_without_auth_header(self, app) -> None:
        """Request without X-User-Id header returns 401."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            response = await client.post(
                "/schedule-groups",
                json={
                    "title": "Weekly 1on1",
                    "counterpart_schedules": [],
                },
            )

        assert response.status_code == 401


class TestCreateScheduleAuth:
    """POST /schedules -- authentication checks."""

    async def test_returns_401_without_auth_header(self, app) -> None:
        """Request without X-User-Id header returns 401."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            response = await client.post(
                "/schedules",
                json={
                    "counterpart_id": str(uuid.uuid4()),
                    "scheduled_at": "2026-04-01T10:00:00+09:00",
                    "title": "Ad-hoc meeting",
                },
            )

        assert response.status_code == 401


class TestListTemplates:
    """GET /templates -- authenticated list."""

    async def test_returns_200_with_empty_list(self, app, user_id: str) -> None:
        """An authenticated user with no templates gets an empty list."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            response = await client.get(
                "/templates",
                headers={"X-User-Id": user_id},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["templates"] == []


class TestSaveTemplate:
    """POST /templates -- template creation."""

    async def test_creates_template_and_returns_201(self, app, user_id: str) -> None:
        """An authenticated user can create a template."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            response = await client.post(
                "/templates",
                headers={"X-User-Id": user_id},
                json={
                    "name": "Weekly Template",
                    "default_counterpart_ids": [],
                    "agenda_topics": ["Progress update", "Blockers"],
                },
            )

        assert response.status_code == 201
        data = response.json()
        assert "template_id" in data
        # Verify it is a valid UUID
        uuid.UUID(data["template_id"])


class TestSendConsultationRequestAuth:
    """POST /schedules/consultation-request -- authentication checks."""

    async def test_returns_401_without_auth_header(self, app) -> None:
        """Request without X-User-Id header returns 401."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            response = await client.post(
                "/schedules/consultation-request",
                json={
                    "organizer_id": str(uuid.uuid4()),
                    "scheduled_at": "2026-04-01T10:00:00+09:00",
                    "title": "Consultation",
                    "agenda_topics": ["Topic 1"],
                },
            )

        assert response.status_code == 401
