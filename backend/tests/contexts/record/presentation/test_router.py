"""Unit tests for the Record context router endpoints.

These tests use httpx.AsyncClient with dependency overrides to mock
application services, verifying request/response mapping, status codes,
and authentication enforcement without requiring a database.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from api.exception_handlers import register_exception_handlers
from contexts.record.application.create_post_hoc_record import (
    CreatePostHocRecordOutput,
    CreatePostHocRecordUseCase,
    SameUserError,
)
from contexts.record.domain.exceptions import UnauthorizedOperationError
from contexts.record.domain.value_objects import RecordId
from contexts.record.presentation.dependencies import (
    get_create_post_hoc_record_use_case,
)
from contexts.record.presentation.router import router
from foundation.auth.dependencies import get_current_user_id
from shared.domain.value_objects import UserId

ACTOR_ID = UserId(value=uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"))
COUNTERPART_ID = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")


def _build_app() -> FastAPI:
    """Create a minimal FastAPI app with the record router."""
    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(router)
    return app


def _override_auth(app: FastAPI) -> None:
    """Override the auth dependency to return a fixed user."""
    app.dependency_overrides[get_current_user_id] = lambda: ACTOR_ID


# -----------------------------------------------------------------------
# POST /records/post-hoc
# -----------------------------------------------------------------------


class TestCreatePostHocRecord:
    """Tests for POST /records/post-hoc."""

    async def test_success_returns_201(self) -> None:
        record_id = RecordId.generate()
        mock_use_case = AsyncMock(spec=CreatePostHocRecordUseCase)
        mock_use_case.execute.return_value = CreatePostHocRecordOutput(
            record_id=record_id,
        )

        app = _build_app()
        _override_auth(app)
        app.dependency_overrides[get_create_post_hoc_record_use_case] = (
            lambda: mock_use_case
        )

        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            response = await client.post(
                "/records/post-hoc",
                json={
                    "counterpart_id": str(COUNTERPART_ID),
                    "conducted_at": "2026-03-25T10:00:00Z",
                },
            )

        assert response.status_code == 201
        assert response.json()["record_id"] == str(record_id.value)
        mock_use_case.execute.assert_awaited_once()

    async def test_same_user_returns_409(self) -> None:
        mock_use_case = AsyncMock(spec=CreatePostHocRecordUseCase)
        mock_use_case.execute.side_effect = SameUserError()

        app = _build_app()
        _override_auth(app)
        app.dependency_overrides[get_create_post_hoc_record_use_case] = (
            lambda: mock_use_case
        )

        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            response = await client.post(
                "/records/post-hoc",
                json={
                    "counterpart_id": str(ACTOR_ID.value),
                    "conducted_at": "2026-03-25T10:00:00Z",
                },
            )

        assert response.status_code == 409

    async def test_unauthorized_returns_403(self) -> None:
        mock_use_case = AsyncMock(spec=CreatePostHocRecordUseCase)
        mock_use_case.execute.side_effect = UnauthorizedOperationError(
            "Only the organizer can create a record."
        )

        app = _build_app()
        _override_auth(app)
        app.dependency_overrides[get_create_post_hoc_record_use_case] = (
            lambda: mock_use_case
        )

        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            response = await client.post(
                "/records/post-hoc",
                json={
                    "counterpart_id": str(COUNTERPART_ID),
                    "conducted_at": "2026-03-25T10:00:00Z",
                },
            )

        assert response.status_code == 403

    async def test_no_auth_returns_401(self) -> None:
        app = _build_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            response = await client.post(
                "/records/post-hoc",
                json={
                    "counterpart_id": str(COUNTERPART_ID),
                    "conducted_at": "2026-03-25T10:00:00Z",
                },
            )

        assert response.status_code == 401
