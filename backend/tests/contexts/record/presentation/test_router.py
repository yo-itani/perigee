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
from contexts.preparation.domain.value_objects import AgendaId, ScheduleId
from contexts.record.application.add_action_item import (
    AddActionItemOutput,
    AddActionItemUseCase,
)
from contexts.record.application.add_action_item import (
    RecordNotFoundError as AddActionItemRecordNotFoundError,
)
from contexts.record.application.confirm_agenda import (
    ConfirmAgendaOutput,
    ConfirmAgendaUseCase,
)
from contexts.record.application.confirm_agenda import (
    RecordNotFoundError as ConfirmAgendaRecordNotFoundError,
)
from contexts.record.application.create_post_hoc_record import (
    CreatePostHocRecordOutput,
    CreatePostHocRecordUseCase,
    SameUserError,
)
from contexts.record.application.create_record_from_schedule import (
    CreateRecordFromScheduleOutput,
    CreateRecordFromScheduleUseCase,
    ScheduleCancelledError,
    ScheduleNotFoundError,
)
from contexts.record.application.delete_action_item import (
    DeleteActionItemOutput,
    DeleteActionItemUseCase,
)
from contexts.record.application.save_draft import (
    RecordNotFoundError as SaveDraftRecordNotFoundError,
)
from contexts.record.application.save_draft import (
    SaveDraftOutput,
    SaveDraftUseCase,
)
from contexts.record.application.update_memo import (
    RecordNotFoundError as UpdateMemoRecordNotFoundError,
)
from contexts.record.application.update_memo import (
    UpdateMemoOutput,
    UpdateMemoUseCase,
)
from contexts.record.domain.exceptions import (
    AgendaAlreadyConfirmedError,
    RecordAlreadyPublishedError,
    UnauthorizedOperationError,
)
from contexts.record.domain.value_objects import ActionItemId, RecordId
from contexts.record.presentation.dependencies import (
    get_add_action_item_use_case,
    get_confirm_agenda_use_case,
    get_create_post_hoc_record_use_case,
    get_create_record_from_schedule_use_case,
    get_delete_action_item_use_case,
    get_save_draft_use_case,
    get_update_memo_use_case,
)
from contexts.record.presentation.router import router
from foundation.auth.dependencies import get_current_user_id
from shared.domain.value_objects import UserId

ACTOR_ID = UserId(value=uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"))
COUNTERPART_ID = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
RECORD_ID = uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
SCHEDULE_ID = uuid.UUID("dddddddd-dddd-dddd-dddd-dddddddddddd")
AGENDA_ID = uuid.UUID("eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee")
ACTION_ITEM_ID = uuid.UUID("ffffffff-ffff-ffff-ffff-ffffffffffff")


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
# POST /records/from-schedule
# -----------------------------------------------------------------------


class TestCreateRecordFromSchedule:
    """Tests for POST /records/from-schedule."""

    async def test_success_returns_201(self) -> None:
        record_id = RecordId.generate()
        mock_use_case = AsyncMock(spec=CreateRecordFromScheduleUseCase)
        mock_use_case.execute.return_value = CreateRecordFromScheduleOutput(
            record_id=record_id,
        )

        app = _build_app()
        _override_auth(app)
        app.dependency_overrides[get_create_record_from_schedule_use_case] = lambda: (
            mock_use_case
        )

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/records/from-schedule",
                json={
                    "schedule_id": str(SCHEDULE_ID),
                    "conducted_at": "2026-03-25T10:00:00Z",
                },
            )

        assert response.status_code == 201
        assert response.json()["record_id"] == str(record_id.value)
        mock_use_case.execute.assert_awaited_once()

    async def test_schedule_not_found_returns_404(self) -> None:
        mock_use_case = AsyncMock(spec=CreateRecordFromScheduleUseCase)
        mock_use_case.execute.side_effect = ScheduleNotFoundError(
            ScheduleId(value=SCHEDULE_ID)
        )

        app = _build_app()
        _override_auth(app)
        app.dependency_overrides[get_create_record_from_schedule_use_case] = lambda: (
            mock_use_case
        )

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/records/from-schedule",
                json={
                    "schedule_id": str(SCHEDULE_ID),
                    "conducted_at": "2026-03-25T10:00:00Z",
                },
            )

        assert response.status_code == 404

    async def test_schedule_cancelled_returns_409(self) -> None:
        mock_use_case = AsyncMock(spec=CreateRecordFromScheduleUseCase)
        mock_use_case.execute.side_effect = ScheduleCancelledError(
            ScheduleId(value=SCHEDULE_ID)
        )

        app = _build_app()
        _override_auth(app)
        app.dependency_overrides[get_create_record_from_schedule_use_case] = lambda: (
            mock_use_case
        )

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/records/from-schedule",
                json={
                    "schedule_id": str(SCHEDULE_ID),
                    "conducted_at": "2026-03-25T10:00:00Z",
                },
            )

        assert response.status_code == 409

    async def test_unauthorized_returns_403(self) -> None:
        mock_use_case = AsyncMock(spec=CreateRecordFromScheduleUseCase)
        mock_use_case.execute.side_effect = UnauthorizedOperationError(
            "Only the organizer can create a record."
        )

        app = _build_app()
        _override_auth(app)
        app.dependency_overrides[get_create_record_from_schedule_use_case] = lambda: (
            mock_use_case
        )

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/records/from-schedule",
                json={
                    "schedule_id": str(SCHEDULE_ID),
                    "conducted_at": "2026-03-25T10:00:00Z",
                },
            )

        assert response.status_code == 403

    async def test_no_auth_returns_401(self) -> None:
        app = _build_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/records/from-schedule",
                json={
                    "schedule_id": str(SCHEDULE_ID),
                    "conducted_at": "2026-03-25T10:00:00Z",
                },
            )

        assert response.status_code == 401


# -----------------------------------------------------------------------
# PUT /records/{id}/memo
# -----------------------------------------------------------------------


class TestUpdateMemo:
    """Tests for PUT /records/{id}/memo."""

    async def test_success_returns_200(self) -> None:
        record_id = RecordId(value=RECORD_ID)
        mock_use_case = AsyncMock(spec=UpdateMemoUseCase)
        mock_use_case.execute.return_value = UpdateMemoOutput(
            record_id=record_id,
        )

        app = _build_app()
        _override_auth(app)
        app.dependency_overrides[get_update_memo_use_case] = lambda: mock_use_case

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.put(
                f"/records/{RECORD_ID}/memo",
                json={"memo": "Some memo content"},
            )

        assert response.status_code == 200
        assert response.json()["record_id"] == str(RECORD_ID)
        mock_use_case.execute.assert_awaited_once()

    async def test_record_not_found_returns_404(self) -> None:
        mock_use_case = AsyncMock(spec=UpdateMemoUseCase)
        mock_use_case.execute.side_effect = UpdateMemoRecordNotFoundError(
            RecordId(value=RECORD_ID)
        )

        app = _build_app()
        _override_auth(app)
        app.dependency_overrides[get_update_memo_use_case] = lambda: mock_use_case

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.put(
                f"/records/{RECORD_ID}/memo",
                json={"memo": "Some memo content"},
            )

        assert response.status_code == 404

    async def test_unauthorized_returns_403(self) -> None:
        mock_use_case = AsyncMock(spec=UpdateMemoUseCase)
        mock_use_case.execute.side_effect = UnauthorizedOperationError(
            "Only the organizer can update the memo."
        )

        app = _build_app()
        _override_auth(app)
        app.dependency_overrides[get_update_memo_use_case] = lambda: mock_use_case

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.put(
                f"/records/{RECORD_ID}/memo",
                json={"memo": "Some memo content"},
            )

        assert response.status_code == 403

    async def test_no_auth_returns_401(self) -> None:
        app = _build_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.put(
                f"/records/{RECORD_ID}/memo",
                json={"memo": "Some memo content"},
            )

        assert response.status_code == 401


# -----------------------------------------------------------------------
# POST /records/{id}/agendas/{agenda_id}/confirm
# -----------------------------------------------------------------------


class TestConfirmAgenda:
    """Tests for POST /records/{id}/agendas/{agenda_id}/confirm."""

    async def test_success_returns_200(self) -> None:
        record_id = RecordId(value=RECORD_ID)
        mock_use_case = AsyncMock(spec=ConfirmAgendaUseCase)
        mock_use_case.execute.return_value = ConfirmAgendaOutput(
            record_id=record_id,
            agenda_id=AgendaId(value=AGENDA_ID),
        )

        app = _build_app()
        _override_auth(app)
        app.dependency_overrides[get_confirm_agenda_use_case] = lambda: mock_use_case

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                f"/records/{RECORD_ID}/agendas/{AGENDA_ID}/confirm",
            )

        assert response.status_code == 200
        assert response.json()["record_id"] == str(RECORD_ID)
        assert response.json()["agenda_id"] == str(AGENDA_ID)
        mock_use_case.execute.assert_awaited_once()

    async def test_record_not_found_returns_404(self) -> None:
        mock_use_case = AsyncMock(spec=ConfirmAgendaUseCase)
        mock_use_case.execute.side_effect = ConfirmAgendaRecordNotFoundError(
            RecordId(value=RECORD_ID)
        )

        app = _build_app()
        _override_auth(app)
        app.dependency_overrides[get_confirm_agenda_use_case] = lambda: mock_use_case

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                f"/records/{RECORD_ID}/agendas/{AGENDA_ID}/confirm",
            )

        assert response.status_code == 404

    async def test_agenda_already_confirmed_returns_409(self) -> None:
        mock_use_case = AsyncMock(spec=ConfirmAgendaUseCase)
        mock_use_case.execute.side_effect = AgendaAlreadyConfirmedError()

        app = _build_app()
        _override_auth(app)
        app.dependency_overrides[get_confirm_agenda_use_case] = lambda: mock_use_case

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                f"/records/{RECORD_ID}/agendas/{AGENDA_ID}/confirm",
            )

        assert response.status_code == 409

    async def test_unauthorized_returns_403(self) -> None:
        mock_use_case = AsyncMock(spec=ConfirmAgendaUseCase)
        mock_use_case.execute.side_effect = UnauthorizedOperationError(
            "Only participants can confirm agendas."
        )

        app = _build_app()
        _override_auth(app)
        app.dependency_overrides[get_confirm_agenda_use_case] = lambda: mock_use_case

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                f"/records/{RECORD_ID}/agendas/{AGENDA_ID}/confirm",
            )

        assert response.status_code == 403

    async def test_no_auth_returns_401(self) -> None:
        app = _build_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                f"/records/{RECORD_ID}/agendas/{AGENDA_ID}/confirm",
            )

        assert response.status_code == 401


# -----------------------------------------------------------------------
# POST /records/{id}/action-items
# -----------------------------------------------------------------------


class TestAddActionItem:
    """Tests for POST /records/{id}/action-items."""

    async def test_success_returns_201(self) -> None:
        action_item_id = ActionItemId(value=ACTION_ITEM_ID)
        mock_use_case = AsyncMock(spec=AddActionItemUseCase)
        mock_use_case.execute.return_value = AddActionItemOutput(
            action_item_id=action_item_id,
        )

        app = _build_app()
        _override_auth(app)
        app.dependency_overrides[get_add_action_item_use_case] = lambda: mock_use_case

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                f"/records/{RECORD_ID}/action-items",
                json={"title": "Follow up on discussion"},
            )

        assert response.status_code == 201
        assert response.json()["action_item_id"] == str(ACTION_ITEM_ID)
        mock_use_case.execute.assert_awaited_once()

    async def test_record_not_found_returns_404(self) -> None:
        mock_use_case = AsyncMock(spec=AddActionItemUseCase)
        mock_use_case.execute.side_effect = AddActionItemRecordNotFoundError(
            RecordId(value=RECORD_ID)
        )

        app = _build_app()
        _override_auth(app)
        app.dependency_overrides[get_add_action_item_use_case] = lambda: mock_use_case

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                f"/records/{RECORD_ID}/action-items",
                json={"title": "Follow up on discussion"},
            )

        assert response.status_code == 404

    async def test_unauthorized_returns_403(self) -> None:
        mock_use_case = AsyncMock(spec=AddActionItemUseCase)
        mock_use_case.execute.side_effect = UnauthorizedOperationError(
            "Only the organizer can add action items."
        )

        app = _build_app()
        _override_auth(app)
        app.dependency_overrides[get_add_action_item_use_case] = lambda: mock_use_case

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                f"/records/{RECORD_ID}/action-items",
                json={"title": "Follow up on discussion"},
            )

        assert response.status_code == 403

    async def test_no_auth_returns_401(self) -> None:
        app = _build_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                f"/records/{RECORD_ID}/action-items",
                json={"title": "Follow up on discussion"},
            )

        assert response.status_code == 401


# -----------------------------------------------------------------------
# DELETE /records/{id}/action-items/{action_item_id}
# -----------------------------------------------------------------------


class TestDeleteActionItem:
    """Tests for DELETE /records/{id}/action-items/{action_item_id}."""

    async def test_success_returns_200(self) -> None:
        action_item_id = ActionItemId(value=ACTION_ITEM_ID)
        mock_use_case = AsyncMock(spec=DeleteActionItemUseCase)
        mock_use_case.execute.return_value = DeleteActionItemOutput(
            action_item_id=action_item_id,
        )

        app = _build_app()
        _override_auth(app)
        app.dependency_overrides[get_delete_action_item_use_case] = lambda: (
            mock_use_case
        )

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.delete(
                f"/records/{RECORD_ID}/action-items/{ACTION_ITEM_ID}",
            )

        assert response.status_code == 200
        assert response.json()["action_item_id"] == str(ACTION_ITEM_ID)
        mock_use_case.execute.assert_awaited_once()

    async def test_unauthorized_returns_403(self) -> None:
        mock_use_case = AsyncMock(spec=DeleteActionItemUseCase)
        mock_use_case.execute.side_effect = UnauthorizedOperationError(
            "Only the organizer can delete action items."
        )

        app = _build_app()
        _override_auth(app)
        app.dependency_overrides[get_delete_action_item_use_case] = lambda: (
            mock_use_case
        )

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.delete(
                f"/records/{RECORD_ID}/action-items/{ACTION_ITEM_ID}",
            )

        assert response.status_code == 403

    async def test_record_already_published_returns_409(self) -> None:
        mock_use_case = AsyncMock(spec=DeleteActionItemUseCase)
        mock_use_case.execute.side_effect = RecordAlreadyPublishedError()

        app = _build_app()
        _override_auth(app)
        app.dependency_overrides[get_delete_action_item_use_case] = lambda: (
            mock_use_case
        )

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.delete(
                f"/records/{RECORD_ID}/action-items/{ACTION_ITEM_ID}",
            )

        assert response.status_code == 409

    async def test_no_auth_returns_401(self) -> None:
        app = _build_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.delete(
                f"/records/{RECORD_ID}/action-items/{ACTION_ITEM_ID}",
            )

        assert response.status_code == 401


# -----------------------------------------------------------------------
# POST /records/{id}/save-draft
# -----------------------------------------------------------------------


class TestSaveDraft:
    """Tests for POST /records/{id}/save-draft."""

    async def test_success_returns_200(self) -> None:
        record_id = RecordId(value=RECORD_ID)
        mock_use_case = AsyncMock(spec=SaveDraftUseCase)
        mock_use_case.execute.return_value = SaveDraftOutput(
            record_id=record_id,
        )

        app = _build_app()
        _override_auth(app)
        app.dependency_overrides[get_save_draft_use_case] = lambda: mock_use_case

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                f"/records/{RECORD_ID}/save-draft",
            )

        assert response.status_code == 200
        assert response.json()["record_id"] == str(RECORD_ID)
        mock_use_case.execute.assert_awaited_once()

    async def test_record_not_found_returns_404(self) -> None:
        mock_use_case = AsyncMock(spec=SaveDraftUseCase)
        mock_use_case.execute.side_effect = SaveDraftRecordNotFoundError(
            RecordId(value=RECORD_ID)
        )

        app = _build_app()
        _override_auth(app)
        app.dependency_overrides[get_save_draft_use_case] = lambda: mock_use_case

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                f"/records/{RECORD_ID}/save-draft",
            )

        assert response.status_code == 404

    async def test_unauthorized_returns_403(self) -> None:
        mock_use_case = AsyncMock(spec=SaveDraftUseCase)
        mock_use_case.execute.side_effect = UnauthorizedOperationError(
            "Only the organizer can save a draft."
        )

        app = _build_app()
        _override_auth(app)
        app.dependency_overrides[get_save_draft_use_case] = lambda: mock_use_case

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                f"/records/{RECORD_ID}/save-draft",
            )

        assert response.status_code == 403

    async def test_record_already_published_returns_409(self) -> None:
        mock_use_case = AsyncMock(spec=SaveDraftUseCase)
        mock_use_case.execute.side_effect = RecordAlreadyPublishedError()

        app = _build_app()
        _override_auth(app)
        app.dependency_overrides[get_save_draft_use_case] = lambda: mock_use_case

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                f"/records/{RECORD_ID}/save-draft",
            )

        assert response.status_code == 409

    async def test_no_auth_returns_401(self) -> None:
        app = _build_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                f"/records/{RECORD_ID}/save-draft",
            )

        assert response.status_code == 401
