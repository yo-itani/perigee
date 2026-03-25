"""Integration tests for Record context API endpoints.

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


class TestCreatePostHocRecordAuth:
    """POST /records/post-hoc -- authentication checks."""

    async def test_returns_401_without_auth_header(self, app) -> None:
        """Request without X-User-Id header returns 401."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            response = await client.post(
                "/records/post-hoc",
                json={
                    "counterpart_id": str(uuid.uuid4()),
                    "conducted_at": "2026-03-20T14:00:00+09:00",
                },
            )

        assert response.status_code == 401


class TestCreatePostHocRecord:
    """POST /records/post-hoc -- authenticated creation."""

    async def test_creates_record_and_returns_201(self, app, user_id: str) -> None:
        """An authenticated user can create a post-hoc record."""
        counterpart_id = str(uuid.uuid4())
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            response = await client.post(
                "/records/post-hoc",
                headers={"X-User-Id": user_id},
                json={
                    "counterpart_id": counterpart_id,
                    "conducted_at": "2026-03-20T14:00:00+09:00",
                },
            )

        assert response.status_code == 201
        data = response.json()
        assert "record_id" in data
        # Verify it is a valid UUID
        uuid.UUID(data["record_id"])
