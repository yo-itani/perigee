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
from contexts.record.application.publish_record import (
    PublishRecordOutput,
    PublishRecordUseCase,
)
from contexts.record.application.publish_record import (
    RecordNotFoundError as PublishRecordNotFoundError,
)
from contexts.record.application.set_viewers import (
    RecordNotFoundError as SetViewersRecordNotFoundError,
)
from contexts.record.application.set_viewers import (
    SetViewersOutput,
    SetViewersUseCase,
)
from contexts.record.application.suggest_default_viewers import (
    RecordNotFoundError as SuggestViewersRecordNotFoundError,
)
from contexts.record.application.suggest_default_viewers import (
    SuggestDefaultViewersOutput,
    SuggestDefaultViewersUseCase,
)
from contexts.record.domain.exceptions import (
    RecordAlreadyPublishedError,
    UnauthorizedOperationError,
)
from contexts.record.domain.value_objects import RecordId
from contexts.record.presentation.dependencies import (
    get_create_post_hoc_record_use_case,
    get_publish_record_use_case,
    get_set_viewers_use_case,
    get_suggest_default_viewers_use_case,
)
from contexts.record.presentation.router import router
from foundation.auth.dependencies import get_current_user_id
from shared.domain.value_objects import UserId

ACTOR_ID = UserId(value=uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"))
COUNTERPART_ID = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
RECORD_ID = uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
VIEWER_ID = uuid.UUID("dddddddd-dddd-dddd-dddd-dddddddddddd")


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
        app.dependency_overrides[get_create_post_hoc_record_use_case] = lambda: (
            mock_use_case
        )

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
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
        app.dependency_overrides[get_create_post_hoc_record_use_case] = lambda: (
            mock_use_case
        )

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
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
        app.dependency_overrides[get_create_post_hoc_record_use_case] = lambda: (
            mock_use_case
        )

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
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
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/records/post-hoc",
                json={
                    "counterpart_id": str(COUNTERPART_ID),
                    "conducted_at": "2026-03-25T10:00:00Z",
                },
            )

        assert response.status_code == 401


# -----------------------------------------------------------------------
# GET /records/{id}/suggested-viewers
# -----------------------------------------------------------------------


class TestGetSuggestedViewers:
    """Tests for GET /records/{id}/suggested-viewers."""

    async def test_success_returns_200(self) -> None:
        viewer = UserId.generate()
        mock_use_case = AsyncMock(spec=SuggestDefaultViewersUseCase)
        mock_use_case.execute.return_value = SuggestDefaultViewersOutput(
            suggested_viewer_ids=[viewer],
        )

        app = _build_app()
        _override_auth(app)
        app.dependency_overrides[get_suggest_default_viewers_use_case] = lambda: (
            mock_use_case
        )

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                f"/records/{RECORD_ID}/suggested-viewers",
            )

        assert response.status_code == 200
        data = response.json()
        assert data["suggested_viewer_ids"] == [str(viewer.value)]
        mock_use_case.execute.assert_awaited_once()

    async def test_record_not_found_returns_404(self) -> None:
        mock_use_case = AsyncMock(spec=SuggestDefaultViewersUseCase)
        mock_use_case.execute.side_effect = SuggestViewersRecordNotFoundError(
            RecordId(value=RECORD_ID)
        )

        app = _build_app()
        _override_auth(app)
        app.dependency_overrides[get_suggest_default_viewers_use_case] = lambda: (
            mock_use_case
        )

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                f"/records/{RECORD_ID}/suggested-viewers",
            )

        assert response.status_code == 404

    async def test_non_organizer_returns_403(self) -> None:
        mock_use_case = AsyncMock(spec=SuggestDefaultViewersUseCase)
        mock_use_case.execute.side_effect = UnauthorizedOperationError(
            "Only the organizer can suggest default viewers."
        )

        app = _build_app()
        _override_auth(app)
        app.dependency_overrides[get_suggest_default_viewers_use_case] = lambda: (
            mock_use_case
        )

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                f"/records/{RECORD_ID}/suggested-viewers",
            )

        assert response.status_code == 403

    async def test_no_auth_returns_401(self) -> None:
        app = _build_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                f"/records/{RECORD_ID}/suggested-viewers",
            )

        assert response.status_code == 401


# -----------------------------------------------------------------------
# PUT /records/{id}/viewers
# -----------------------------------------------------------------------


class TestSetViewers:
    """Tests for PUT /records/{id}/viewers."""

    async def test_success_returns_200(self) -> None:
        mock_use_case = AsyncMock(spec=SetViewersUseCase)
        mock_use_case.execute.return_value = SetViewersOutput(
            record_id=RecordId(value=RECORD_ID),
        )

        app = _build_app()
        _override_auth(app)
        app.dependency_overrides[get_set_viewers_use_case] = lambda: mock_use_case

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.put(
                f"/records/{RECORD_ID}/viewers",
                json={"viewer_ids": [str(VIEWER_ID)]},
            )

        assert response.status_code == 200
        assert response.json()["record_id"] == str(RECORD_ID)
        mock_use_case.execute.assert_awaited_once()

    async def test_record_not_found_returns_404(self) -> None:
        mock_use_case = AsyncMock(spec=SetViewersUseCase)
        mock_use_case.execute.side_effect = SetViewersRecordNotFoundError(
            RecordId(value=RECORD_ID)
        )

        app = _build_app()
        _override_auth(app)
        app.dependency_overrides[get_set_viewers_use_case] = lambda: mock_use_case

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.put(
                f"/records/{RECORD_ID}/viewers",
                json={"viewer_ids": [str(VIEWER_ID)]},
            )

        assert response.status_code == 404

    async def test_non_organizer_returns_403(self) -> None:
        mock_use_case = AsyncMock(spec=SetViewersUseCase)
        mock_use_case.execute.side_effect = UnauthorizedOperationError(
            "Only the organizer can edit the record."
        )

        app = _build_app()
        _override_auth(app)
        app.dependency_overrides[get_set_viewers_use_case] = lambda: mock_use_case

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.put(
                f"/records/{RECORD_ID}/viewers",
                json={"viewer_ids": [str(VIEWER_ID)]},
            )

        assert response.status_code == 403

    async def test_no_auth_returns_401(self) -> None:
        app = _build_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.put(
                f"/records/{RECORD_ID}/viewers",
                json={"viewer_ids": [str(VIEWER_ID)]},
            )

        assert response.status_code == 401


# -----------------------------------------------------------------------
# POST /records/{id}/publish
# -----------------------------------------------------------------------


class TestPublishRecord:
    """Tests for POST /records/{id}/publish."""

    async def test_success_returns_200(self) -> None:
        mock_use_case = AsyncMock(spec=PublishRecordUseCase)
        mock_use_case.execute.return_value = PublishRecordOutput(
            record_id=RecordId(value=RECORD_ID),
        )

        app = _build_app()
        _override_auth(app)
        app.dependency_overrides[get_publish_record_use_case] = lambda: mock_use_case

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                f"/records/{RECORD_ID}/publish",
                json={"viewer_ids": [str(VIEWER_ID)]},
            )

        assert response.status_code == 200
        assert response.json()["record_id"] == str(RECORD_ID)
        mock_use_case.execute.assert_awaited_once()

    async def test_record_not_found_returns_404(self) -> None:
        mock_use_case = AsyncMock(spec=PublishRecordUseCase)
        mock_use_case.execute.side_effect = PublishRecordNotFoundError(
            RecordId(value=RECORD_ID)
        )

        app = _build_app()
        _override_auth(app)
        app.dependency_overrides[get_publish_record_use_case] = lambda: mock_use_case

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                f"/records/{RECORD_ID}/publish",
                json={"viewer_ids": [str(VIEWER_ID)]},
            )

        assert response.status_code == 404

    async def test_non_organizer_returns_403(self) -> None:
        mock_use_case = AsyncMock(spec=PublishRecordUseCase)
        mock_use_case.execute.side_effect = UnauthorizedOperationError(
            "Only the organizer can edit the record."
        )

        app = _build_app()
        _override_auth(app)
        app.dependency_overrides[get_publish_record_use_case] = lambda: mock_use_case

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                f"/records/{RECORD_ID}/publish",
                json={"viewer_ids": [str(VIEWER_ID)]},
            )

        assert response.status_code == 403

    async def test_already_published_returns_409(self) -> None:
        mock_use_case = AsyncMock(spec=PublishRecordUseCase)
        mock_use_case.execute.side_effect = RecordAlreadyPublishedError()

        app = _build_app()
        _override_auth(app)
        app.dependency_overrides[get_publish_record_use_case] = lambda: mock_use_case

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                f"/records/{RECORD_ID}/publish",
                json={"viewer_ids": [str(VIEWER_ID)]},
            )

        assert response.status_code == 409

    async def test_no_auth_returns_401(self) -> None:
        app = _build_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                f"/records/{RECORD_ID}/publish",
                json={"viewer_ids": [str(VIEWER_ID)]},
            )

        assert response.status_code == 401
