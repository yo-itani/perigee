"""Unit tests for the Preparation context router endpoints.

These tests use httpx.AsyncClient with dependency overrides to mock
application services, verifying request/response mapping, status codes,
and authentication enforcement without requiring a database.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from api.exception_handlers import register_exception_handlers
from contexts.preparation.application.accept_consultation_request_service import (
    AcceptConsultationRequestService,
)
from contexts.preparation.application.accept_consultation_request_service import (
    ScheduleNotFoundError as AcceptScheduleNotFoundError,
)
from contexts.preparation.application.add_agenda_comment_service import (
    AddAgendaCommentOutput,
    AddAgendaCommentService,
    UnauthorizedAgendaCommentError,
)
from contexts.preparation.application.add_agenda_comment_service import (
    AgendaNotFoundError as AgendaCommentAgendaNotFoundError,
)
from contexts.preparation.application.add_agenda_service import (
    AddAgendaOutput,
    AddAgendaService,
)
from contexts.preparation.application.add_agenda_service import (
    ScheduleNotFoundError as AddAgendaScheduleNotFoundError,
)
from contexts.preparation.application.add_agenda_service import (
    UnauthorizedAgendaOperationError as AddAgendaUnauthorizedError,
)
from contexts.preparation.application.cancel_schedule_service import (
    CancelScheduleService,
)
from contexts.preparation.application.cancel_schedule_service import (
    ScheduleNotFoundError as CancelScheduleNotFoundError,
)
from contexts.preparation.application.create_schedule_group_from_past_service import (
    CreateScheduleGroupFromPastOutput,
    CreateScheduleGroupFromPastService,
)
from contexts.preparation.application.create_schedule_group_from_template_service import (  # noqa: E501
    CreateScheduleGroupFromTemplateOutput,
    CreateScheduleGroupFromTemplateService,
)
from contexts.preparation.application.create_schedule_group_service import (
    CreateScheduleGroupOutput,
    CreateScheduleGroupService,
)
from contexts.preparation.application.create_schedule_service import (
    CreateScheduleOutput,
    CreateScheduleService,
)
from contexts.preparation.application.delete_agenda_service import (
    AgendaNotFoundError as DeleteAgendaNotFoundError,
)
from contexts.preparation.application.delete_agenda_service import (
    DeleteAgendaService,
)
from contexts.preparation.application.delete_agenda_service import (
    UnauthorizedAgendaOperationError as DeleteAgendaUnauthorizedError,
)
from contexts.preparation.application.get_schedule_detail_service import (
    GetScheduleDetailOutput,
    GetScheduleDetailService,
)
from contexts.preparation.application.get_schedule_detail_service import (
    ScheduleNotFoundError as GetScheduleDetailNotFoundError,
)
from contexts.preparation.application.get_template_service import (
    GetTemplateOutput,
    GetTemplateService,
    TemplateNotFoundError,
    UnauthorizedTemplateAccessError,
)
from contexts.preparation.application.list_schedule_agendas_service import (
    ListScheduleAgendasOutput,
    ListScheduleAgendasService,
)
from contexts.preparation.application.list_schedule_agendas_service import (
    ScheduleNotFoundError as ListAgendasScheduleNotFoundError,
)
from contexts.preparation.application.list_templates_service import (
    ListTemplatesOutput,
    ListTemplatesService,
    TemplateListItem,
)
from contexts.preparation.application.list_upcoming_schedules_service import (
    ListUpcomingSchedulesOutput,
    ListUpcomingSchedulesService,
    UpcomingScheduleItem,
)
from contexts.preparation.application.reject_consultation_request_service import (
    RejectConsultationRequestService,
)
from contexts.preparation.application.reject_consultation_request_service import (
    ScheduleNotFoundError as RejectScheduleNotFoundError,
)
from contexts.preparation.application.rename_schedule_service import (
    RenameScheduleService,
    UnauthorizedRenameError,
)
from contexts.preparation.application.rename_schedule_service import (
    ScheduleNotFoundError as RenameScheduleNotFoundError,
)
from contexts.preparation.application.reschedule_service import (
    RescheduleService,
)
from contexts.preparation.application.reschedule_service import (
    ScheduleNotFoundError as RescheduleScheduleNotFoundError,
)
from contexts.preparation.application.save_template_service import (
    SaveTemplateOutput,
    SaveTemplateService,
)
from contexts.preparation.application.send_consultation_request_service import (
    SendConsultationRequestOutput,
    SendConsultationRequestService,
)
from contexts.preparation.domain.exceptions import (
    UnauthorizedScheduleOperationError,
)
from contexts.preparation.domain.value_objects import (
    AgendaId,
    CommentId,
    ScheduleGroupId,
    ScheduleId,
    ScheduleStatus,
    TemplateId,
)
from contexts.preparation.presentation.dependencies import (
    get_accept_consultation_request_service,
    get_add_agenda_comment_service,
    get_add_agenda_service,
    get_cancel_schedule_service,
    get_create_schedule_group_from_past_service,
    get_create_schedule_group_from_template_service,
    get_create_schedule_group_service,
    get_create_schedule_service,
    get_delete_agenda_service,
    get_get_last_session_summary_service,
    get_get_schedule_detail_service,
    get_get_template_service,
    get_list_schedule_agendas_service,
    get_list_templates_service,
    get_list_upcoming_schedules_service,
    get_reject_consultation_request_service,
    get_rename_schedule_service,
    get_reschedule_service,
    get_save_template_service,
    get_send_consultation_request_service,
)
from contexts.preparation.presentation.router import router
from contexts.record.application.get_last_session_summary import (
    ActionItemSummaryDTO,
    GetLastSessionSummaryOutput,
    GetLastSessionSummaryQueryService,
)
from contexts.record.domain.value_objects import ActionItemId, RecordId
from foundation.auth.dependencies import get_current_user_id
from shared.domain.value_objects import UserId

ACTOR_ID = UserId(value=uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"))
COUNTERPART_ID = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")


def _build_app() -> FastAPI:
    """Create a minimal FastAPI app with the preparation router."""
    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(router)
    return app


def _override_auth(app: FastAPI) -> None:
    """Override the auth dependency to return a fixed user."""
    app.dependency_overrides[get_current_user_id] = lambda: ACTOR_ID


# -----------------------------------------------------------------------
# POST /schedule-groups
# -----------------------------------------------------------------------


class TestCreateScheduleGroup:
    """Tests for POST /schedule-groups."""

    async def test_success_returns_201(self) -> None:
        group_id = ScheduleGroupId.generate()
        mock_service = AsyncMock(spec=CreateScheduleGroupService)
        mock_service.execute.return_value = CreateScheduleGroupOutput(
            schedule_group_id=group_id,
        )

        app = _build_app()
        _override_auth(app)
        app.dependency_overrides[get_create_schedule_group_service] = lambda: (
            mock_service
        )

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/schedule-groups",
                json={
                    "title": "Weekly 1on1",
                    "counterpart_schedules": [
                        {
                            "counterpart_id": str(COUNTERPART_ID),
                            "scheduled_at": "2026-04-01T10:00:00Z",
                        },
                    ],
                },
            )

        assert response.status_code == 201
        body = response.json()
        assert body["schedule_group_id"] == str(group_id.value)
        mock_service.execute.assert_awaited_once()

    async def test_no_auth_returns_401(self) -> None:
        app = _build_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/schedule-groups",
                json={
                    "title": "Weekly 1on1",
                    "counterpart_schedules": [],
                },
            )

        assert response.status_code == 401


# -----------------------------------------------------------------------
# POST /schedule-groups/from-template
# -----------------------------------------------------------------------


class TestCreateScheduleGroupFromTemplate:
    """Tests for POST /schedule-groups/from-template."""

    async def test_success_returns_201(self) -> None:
        group_id = ScheduleGroupId.generate()
        mock_service = AsyncMock(spec=CreateScheduleGroupFromTemplateService)
        mock_service.execute.return_value = CreateScheduleGroupFromTemplateOutput(
            schedule_group_id=group_id
        )

        app = _build_app()
        _override_auth(app)
        app.dependency_overrides[get_create_schedule_group_from_template_service] = (
            lambda: mock_service
        )

        template_id = str(uuid.uuid4())
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/schedule-groups/from-template",
                json={
                    "template_id": template_id,
                    "title": "From template",
                    "counterpart_schedules": [
                        {
                            "counterpart_id": str(COUNTERPART_ID),
                            "scheduled_at": "2026-04-01T10:00:00Z",
                        },
                    ],
                },
            )

        assert response.status_code == 201
        assert response.json()["schedule_group_id"] == str(group_id.value)

    async def test_no_auth_returns_401(self) -> None:
        app = _build_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/schedule-groups/from-template",
                json={
                    "template_id": str(uuid.uuid4()),
                    "title": "Test",
                    "counterpart_schedules": [],
                },
            )

        assert response.status_code == 401


# -----------------------------------------------------------------------
# POST /schedule-groups/from-past
# -----------------------------------------------------------------------


class TestCreateScheduleGroupFromPast:
    """Tests for POST /schedule-groups/from-past."""

    async def test_success_returns_201(self) -> None:
        group_id = ScheduleGroupId.generate()
        mock_service = AsyncMock(spec=CreateScheduleGroupFromPastService)
        mock_service.execute.return_value = CreateScheduleGroupFromPastOutput(
            schedule_group_id=group_id
        )

        app = _build_app()
        _override_auth(app)
        _dep = get_create_schedule_group_from_past_service
        app.dependency_overrides[_dep] = lambda: mock_service

        source_id = str(uuid.uuid4())
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/schedule-groups/from-past",
                json={
                    "source_schedule_group_id": source_id,
                    "title": "From past",
                    "counterpart_schedules": [
                        {
                            "counterpart_id": str(COUNTERPART_ID),
                            "scheduled_at": "2026-04-01T10:00:00Z",
                        },
                    ],
                },
            )

        assert response.status_code == 201
        assert response.json()["schedule_group_id"] == str(group_id.value)

    async def test_no_auth_returns_401(self) -> None:
        app = _build_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/schedule-groups/from-past",
                json={
                    "source_schedule_group_id": str(uuid.uuid4()),
                    "title": "Test",
                    "counterpart_schedules": [],
                },
            )

        assert response.status_code == 401


# -----------------------------------------------------------------------
# POST /schedules
# -----------------------------------------------------------------------


class TestCreateSchedule:
    """Tests for POST /schedules."""

    async def test_success_returns_201(self) -> None:
        schedule_id = ScheduleId.generate()
        mock_service = AsyncMock(spec=CreateScheduleService)
        mock_service.execute.return_value = CreateScheduleOutput(
            schedule_id=schedule_id,
        )

        app = _build_app()
        _override_auth(app)
        app.dependency_overrides[get_create_schedule_service] = lambda: mock_service

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/schedules",
                json={
                    "counterpart_id": str(COUNTERPART_ID),
                    "scheduled_at": "2026-04-01T10:00:00Z",
                    "title": "1-on-1",
                },
            )

        assert response.status_code == 201
        assert response.json()["schedule_id"] == str(schedule_id.value)

    async def test_no_auth_returns_401(self) -> None:
        app = _build_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/schedules",
                json={
                    "counterpart_id": str(COUNTERPART_ID),
                    "scheduled_at": "2026-04-01T10:00:00Z",
                    "title": "1-on-1",
                },
            )

        assert response.status_code == 401


# -----------------------------------------------------------------------
# POST /schedules/consultation-request
# -----------------------------------------------------------------------


class TestSendConsultationRequest:
    """Tests for POST /schedules/consultation-request."""

    async def test_success_returns_201(self) -> None:
        schedule_id = ScheduleId.generate()
        mock_service = AsyncMock(spec=SendConsultationRequestService)
        mock_service.execute.return_value = SendConsultationRequestOutput(
            schedule_id=schedule_id,
        )

        app = _build_app()
        _override_auth(app)
        app.dependency_overrides[get_send_consultation_request_service] = lambda: (
            mock_service
        )

        organizer_id = str(uuid.uuid4())
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/schedules/consultation-request",
                json={
                    "organizer_id": organizer_id,
                    "scheduled_at": "2026-04-01T10:00:00Z",
                    "title": "Need advice",
                    "agenda_topics": ["Topic A"],
                },
            )

        assert response.status_code == 201
        assert response.json()["schedule_id"] == str(schedule_id.value)

    async def test_no_auth_returns_401(self) -> None:
        app = _build_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/schedules/consultation-request",
                json={
                    "organizer_id": str(uuid.uuid4()),
                    "scheduled_at": "2026-04-01T10:00:00Z",
                    "title": "Need advice",
                    "agenda_topics": ["Topic A"],
                },
            )

        assert response.status_code == 401


# -----------------------------------------------------------------------
# GET /schedules/upcoming
# -----------------------------------------------------------------------


class TestListUpcomingSchedules:
    """Tests for GET /schedules/upcoming."""

    async def test_success_returns_200(self) -> None:
        schedule_id = ScheduleId.generate()
        now = datetime.now(UTC)
        mock_service = AsyncMock(spec=ListUpcomingSchedulesService)
        mock_service.execute.return_value = ListUpcomingSchedulesOutput(
            schedules=[
                UpcomingScheduleItem(
                    schedule_id=schedule_id,
                    organizer_id=ACTOR_ID,
                    counterpart_id=UserId(value=COUNTERPART_ID),
                    scheduled_at=now,
                    status=ScheduleStatus.CONFIRMED,
                    title="Weekly 1on1",
                    schedule_group_id=None,
                ),
            ],
        )

        app = _build_app()
        _override_auth(app)
        app.dependency_overrides[get_list_upcoming_schedules_service] = lambda: (
            mock_service
        )

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/schedules/upcoming")

        assert response.status_code == 200
        body = response.json()
        assert len(body["schedules"]) == 1
        assert body["schedules"][0]["schedule_id"] == str(schedule_id.value)
        assert body["schedules"][0]["title"] == "Weekly 1on1"
        assert body["schedules"][0]["status"] == "confirmed"

    async def test_no_auth_returns_401(self) -> None:
        app = _build_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/schedules/upcoming")

        assert response.status_code == 401


# -----------------------------------------------------------------------
# GET /schedules/{schedule_id}
# -----------------------------------------------------------------------


class TestGetScheduleDetail:
    """Tests for GET /schedules/{schedule_id}."""

    async def test_success_returns_200(self) -> None:
        schedule_id = ScheduleId.generate()
        now = datetime.now(UTC)
        mock_service = AsyncMock(spec=GetScheduleDetailService)
        mock_service.execute.return_value = GetScheduleDetailOutput(
            schedule_id=schedule_id,
            organizer_id=ACTOR_ID,
            counterpart_id=UserId(value=COUNTERPART_ID),
            title="Weekly 1on1",
            scheduled_at=now,
            status=ScheduleStatus.CONFIRMED,
            schedule_group_id=None,
            created_at=now,
            updated_at=now,
        )

        app = _build_app()
        _override_auth(app)
        app.dependency_overrides[get_get_schedule_detail_service] = lambda: mock_service

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(f"/schedules/{schedule_id.value}")

        assert response.status_code == 200
        body = response.json()
        assert body["schedule_id"] == str(schedule_id.value)
        assert body["title"] == "Weekly 1on1"
        assert body["status"] == "confirmed"

    async def test_not_found_returns_404(self) -> None:
        schedule_id = ScheduleId.generate()
        mock_service = AsyncMock(spec=GetScheduleDetailService)
        mock_service.execute.side_effect = GetScheduleDetailNotFoundError(schedule_id)

        app = _build_app()
        _override_auth(app)
        app.dependency_overrides[get_get_schedule_detail_service] = lambda: mock_service

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(f"/schedules/{schedule_id.value}")

        assert response.status_code == 404

    async def test_unauthorized_returns_403(self) -> None:
        mock_service = AsyncMock(spec=GetScheduleDetailService)
        mock_service.execute.side_effect = UnauthorizedScheduleOperationError(
            "Only the organizer or counterpart can view schedule details."
        )

        app = _build_app()
        _override_auth(app)
        app.dependency_overrides[get_get_schedule_detail_service] = lambda: mock_service

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(f"/schedules/{uuid.uuid4()}")

        assert response.status_code == 403

    async def test_no_auth_returns_401(self) -> None:
        app = _build_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(f"/schedules/{uuid.uuid4()}")

        assert response.status_code == 401


# -----------------------------------------------------------------------
# GET /schedules/{schedule_id}/agendas
# -----------------------------------------------------------------------


class TestListScheduleAgendas:
    """Tests for GET /schedules/{schedule_id}/agendas."""

    async def test_success_returns_200(self) -> None:
        mock_service = AsyncMock(spec=ListScheduleAgendasService)
        mock_service.execute.return_value = ListScheduleAgendasOutput(
            agendas=[],
        )

        app = _build_app()
        _override_auth(app)
        app.dependency_overrides[get_list_schedule_agendas_service] = lambda: (
            mock_service
        )

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(f"/schedules/{uuid.uuid4()}/agendas")

        assert response.status_code == 200
        assert response.json()["agendas"] == []

    async def test_not_found_returns_404(self) -> None:
        schedule_id = ScheduleId.generate()
        mock_service = AsyncMock(spec=ListScheduleAgendasService)
        mock_service.execute.side_effect = ListAgendasScheduleNotFoundError(schedule_id)

        app = _build_app()
        _override_auth(app)
        app.dependency_overrides[get_list_schedule_agendas_service] = lambda: (
            mock_service
        )

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(f"/schedules/{schedule_id.value}/agendas")

        assert response.status_code == 404

    async def test_unauthorized_returns_403(self) -> None:
        mock_service = AsyncMock(spec=ListScheduleAgendasService)
        mock_service.execute.side_effect = UnauthorizedScheduleOperationError(
            "Only the organizer or counterpart can view agendas."
        )

        app = _build_app()
        _override_auth(app)
        app.dependency_overrides[get_list_schedule_agendas_service] = lambda: (
            mock_service
        )

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(f"/schedules/{uuid.uuid4()}/agendas")

        assert response.status_code == 403

    async def test_no_auth_returns_401(self) -> None:
        app = _build_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(f"/schedules/{uuid.uuid4()}/agendas")

        assert response.status_code == 401


# -----------------------------------------------------------------------
# POST /schedules/{schedule_id}/confirm
# -----------------------------------------------------------------------


class TestConfirmSchedule:
    """Tests for POST /schedules/{schedule_id}/confirm."""

    async def test_success_returns_204(self) -> None:
        mock_service = AsyncMock(spec=AcceptConsultationRequestService)
        mock_service.execute.return_value = None

        app = _build_app()
        _override_auth(app)
        app.dependency_overrides[get_accept_consultation_request_service] = lambda: (
            mock_service
        )

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(f"/schedules/{uuid.uuid4()}/confirm")

        assert response.status_code == 204
        mock_service.execute.assert_awaited_once()

    async def test_not_found_returns_404(self) -> None:
        schedule_id = ScheduleId.generate()
        mock_service = AsyncMock(spec=AcceptConsultationRequestService)
        mock_service.execute.side_effect = AcceptScheduleNotFoundError(schedule_id)

        app = _build_app()
        _override_auth(app)
        app.dependency_overrides[get_accept_consultation_request_service] = lambda: (
            mock_service
        )

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(f"/schedules/{schedule_id.value}/confirm")

        assert response.status_code == 404

    async def test_unauthorized_returns_403(self) -> None:
        mock_service = AsyncMock(spec=AcceptConsultationRequestService)
        mock_service.execute.side_effect = UnauthorizedScheduleOperationError(
            "Only the organizer can accept a consultation request."
        )

        app = _build_app()
        _override_auth(app)
        app.dependency_overrides[get_accept_consultation_request_service] = lambda: (
            mock_service
        )

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(f"/schedules/{uuid.uuid4()}/confirm")

        assert response.status_code == 403

    async def test_no_auth_returns_401(self) -> None:
        app = _build_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(f"/schedules/{uuid.uuid4()}/confirm")

        assert response.status_code == 401


# -----------------------------------------------------------------------
# POST /schedules/{schedule_id}/reject
# -----------------------------------------------------------------------


class TestRejectSchedule:
    """Tests for POST /schedules/{schedule_id}/reject."""

    async def test_success_returns_204(self) -> None:
        mock_service = AsyncMock(spec=RejectConsultationRequestService)
        mock_service.execute.return_value = None

        app = _build_app()
        _override_auth(app)
        app.dependency_overrides[get_reject_consultation_request_service] = lambda: (
            mock_service
        )

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(f"/schedules/{uuid.uuid4()}/reject")

        assert response.status_code == 204

    async def test_not_found_returns_404(self) -> None:
        schedule_id = ScheduleId.generate()
        mock_service = AsyncMock(spec=RejectConsultationRequestService)
        mock_service.execute.side_effect = RejectScheduleNotFoundError(schedule_id)

        app = _build_app()
        _override_auth(app)
        app.dependency_overrides[get_reject_consultation_request_service] = lambda: (
            mock_service
        )

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(f"/schedules/{schedule_id.value}/reject")

        assert response.status_code == 404

    async def test_unauthorized_returns_403(self) -> None:
        mock_service = AsyncMock(spec=RejectConsultationRequestService)
        mock_service.execute.side_effect = UnauthorizedScheduleOperationError(
            "Only the organizer can reject a consultation request."
        )

        app = _build_app()
        _override_auth(app)
        app.dependency_overrides[get_reject_consultation_request_service] = lambda: (
            mock_service
        )

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(f"/schedules/{uuid.uuid4()}/reject")

        assert response.status_code == 403

    async def test_no_auth_returns_401(self) -> None:
        app = _build_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(f"/schedules/{uuid.uuid4()}/reject")

        assert response.status_code == 401


# -----------------------------------------------------------------------
# POST /schedules/{schedule_id}/reschedule
# -----------------------------------------------------------------------


class TestReschedule:
    """Tests for POST /schedules/{schedule_id}/reschedule."""

    async def test_success_returns_204(self) -> None:
        mock_service = AsyncMock(spec=RescheduleService)
        mock_service.execute.return_value = None

        app = _build_app()
        _override_auth(app)
        app.dependency_overrides[get_reschedule_service] = lambda: mock_service

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                f"/schedules/{uuid.uuid4()}/reschedule",
                json={"new_scheduled_at": "2026-05-01T10:00:00Z"},
            )

        assert response.status_code == 204

    async def test_not_found_returns_404(self) -> None:
        schedule_id = ScheduleId.generate()
        mock_service = AsyncMock(spec=RescheduleService)
        mock_service.execute.side_effect = RescheduleScheduleNotFoundError(schedule_id)

        app = _build_app()
        _override_auth(app)
        app.dependency_overrides[get_reschedule_service] = lambda: mock_service

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                f"/schedules/{schedule_id.value}/reschedule",
                json={"new_scheduled_at": "2026-05-01T10:00:00Z"},
            )

        assert response.status_code == 404

    async def test_unauthorized_returns_403(self) -> None:
        mock_service = AsyncMock(spec=RescheduleService)
        mock_service.execute.side_effect = UnauthorizedScheduleOperationError(
            "Only the organizer or counterpart can reschedule."
        )

        app = _build_app()
        _override_auth(app)
        app.dependency_overrides[get_reschedule_service] = lambda: mock_service

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                f"/schedules/{uuid.uuid4()}/reschedule",
                json={"new_scheduled_at": "2026-05-01T10:00:00Z"},
            )

        assert response.status_code == 403

    async def test_no_auth_returns_401(self) -> None:
        app = _build_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                f"/schedules/{uuid.uuid4()}/reschedule",
                json={"new_scheduled_at": "2026-05-01T10:00:00Z"},
            )

        assert response.status_code == 401


# -----------------------------------------------------------------------
# POST /schedules/{schedule_id}/cancel
# -----------------------------------------------------------------------


class TestCancelSchedule:
    """Tests for POST /schedules/{schedule_id}/cancel."""

    async def test_success_returns_204(self) -> None:
        mock_service = AsyncMock(spec=CancelScheduleService)
        mock_service.execute.return_value = None

        app = _build_app()
        _override_auth(app)
        app.dependency_overrides[get_cancel_schedule_service] = lambda: mock_service

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(f"/schedules/{uuid.uuid4()}/cancel")

        assert response.status_code == 204

    async def test_not_found_returns_404(self) -> None:
        schedule_id = ScheduleId.generate()
        mock_service = AsyncMock(spec=CancelScheduleService)
        mock_service.execute.side_effect = CancelScheduleNotFoundError(schedule_id)

        app = _build_app()
        _override_auth(app)
        app.dependency_overrides[get_cancel_schedule_service] = lambda: mock_service

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(f"/schedules/{schedule_id.value}/cancel")

        assert response.status_code == 404

    async def test_unauthorized_returns_403(self) -> None:
        mock_service = AsyncMock(spec=CancelScheduleService)
        mock_service.execute.side_effect = UnauthorizedScheduleOperationError(
            "Only the organizer or counterpart can cancel."
        )

        app = _build_app()
        _override_auth(app)
        app.dependency_overrides[get_cancel_schedule_service] = lambda: mock_service

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(f"/schedules/{uuid.uuid4()}/cancel")

        assert response.status_code == 403

    async def test_no_auth_returns_401(self) -> None:
        app = _build_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(f"/schedules/{uuid.uuid4()}/cancel")

        assert response.status_code == 401


# -----------------------------------------------------------------------
# PUT /schedules/{schedule_id}/title
# -----------------------------------------------------------------------


class TestRenameSchedule:
    """Tests for PUT /schedules/{schedule_id}/title."""

    async def test_success_returns_204(self) -> None:
        mock_service = AsyncMock(spec=RenameScheduleService)
        mock_service.execute.return_value = None

        app = _build_app()
        _override_auth(app)
        app.dependency_overrides[get_rename_schedule_service] = lambda: mock_service

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.put(
                f"/schedules/{uuid.uuid4()}/title",
                json={"title": "New Title"},
            )

        assert response.status_code == 204

    async def test_not_found_returns_404(self) -> None:
        schedule_id = ScheduleId.generate()
        mock_service = AsyncMock(spec=RenameScheduleService)
        mock_service.execute.side_effect = RenameScheduleNotFoundError(schedule_id)

        app = _build_app()
        _override_auth(app)
        app.dependency_overrides[get_rename_schedule_service] = lambda: mock_service

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.put(
                f"/schedules/{schedule_id.value}/title",
                json={"title": "New Title"},
            )

        assert response.status_code == 404

    async def test_unauthorized_returns_403(self) -> None:
        mock_service = AsyncMock(spec=RenameScheduleService)
        mock_service.execute.side_effect = UnauthorizedRenameError()

        app = _build_app()
        _override_auth(app)
        app.dependency_overrides[get_rename_schedule_service] = lambda: mock_service

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.put(
                f"/schedules/{uuid.uuid4()}/title",
                json={"title": "New Title"},
            )

        assert response.status_code == 403

    async def test_no_auth_returns_401(self) -> None:
        app = _build_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.put(
                f"/schedules/{uuid.uuid4()}/title",
                json={"title": "New Title"},
            )

        assert response.status_code == 401


# -----------------------------------------------------------------------
# POST /schedules/{schedule_id}/agendas
# -----------------------------------------------------------------------


class TestAddAgenda:
    """Tests for POST /schedules/{schedule_id}/agendas."""

    async def test_success_returns_201(self) -> None:
        agenda_id = AgendaId.generate()
        mock_service = AsyncMock(spec=AddAgendaService)
        mock_service.execute.return_value = AddAgendaOutput(agenda_id=agenda_id)

        app = _build_app()
        _override_auth(app)
        app.dependency_overrides[get_add_agenda_service] = lambda: mock_service

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                f"/schedules/{uuid.uuid4()}/agendas",
                json={"topic": "Discuss project roadmap"},
            )

        assert response.status_code == 201
        assert response.json()["agenda_id"] == str(agenda_id.value)

    async def test_not_found_returns_404(self) -> None:
        schedule_id = ScheduleId.generate()
        mock_service = AsyncMock(spec=AddAgendaService)
        mock_service.execute.side_effect = AddAgendaScheduleNotFoundError(schedule_id)

        app = _build_app()
        _override_auth(app)
        app.dependency_overrides[get_add_agenda_service] = lambda: mock_service

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                f"/schedules/{schedule_id.value}/agendas",
                json={"topic": "Discuss project roadmap"},
            )

        assert response.status_code == 404

    async def test_unauthorized_returns_403(self) -> None:
        mock_service = AsyncMock(spec=AddAgendaService)
        mock_service.execute.side_effect = AddAgendaUnauthorizedError()

        app = _build_app()
        _override_auth(app)
        app.dependency_overrides[get_add_agenda_service] = lambda: mock_service

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                f"/schedules/{uuid.uuid4()}/agendas",
                json={"topic": "Discuss project roadmap"},
            )

        assert response.status_code == 403

    async def test_no_auth_returns_401(self) -> None:
        app = _build_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                f"/schedules/{uuid.uuid4()}/agendas",
                json={"topic": "Discuss project roadmap"},
            )

        assert response.status_code == 401


# -----------------------------------------------------------------------
# DELETE /schedules/{schedule_id}/agendas/{agenda_id}
# -----------------------------------------------------------------------


class TestDeleteAgenda:
    """Tests for DELETE /schedules/{schedule_id}/agendas/{agenda_id}."""

    async def test_success_returns_204(self) -> None:
        mock_service = AsyncMock(spec=DeleteAgendaService)
        mock_service.execute.return_value = None

        app = _build_app()
        _override_auth(app)
        app.dependency_overrides[get_delete_agenda_service] = lambda: mock_service

        schedule_id = uuid.uuid4()
        agenda_id = uuid.uuid4()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.delete(
                f"/schedules/{schedule_id}/agendas/{agenda_id}"
            )

        assert response.status_code == 204

    async def test_agenda_not_found_returns_404(self) -> None:
        agenda_id = AgendaId.generate()
        mock_service = AsyncMock(spec=DeleteAgendaService)
        mock_service.execute.side_effect = DeleteAgendaNotFoundError(agenda_id)

        app = _build_app()
        _override_auth(app)
        app.dependency_overrides[get_delete_agenda_service] = lambda: mock_service

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.delete(
                f"/schedules/{uuid.uuid4()}/agendas/{agenda_id.value}"
            )

        assert response.status_code == 404

    async def test_unauthorized_returns_403(self) -> None:
        mock_service = AsyncMock(spec=DeleteAgendaService)
        mock_service.execute.side_effect = DeleteAgendaUnauthorizedError()

        app = _build_app()
        _override_auth(app)
        app.dependency_overrides[get_delete_agenda_service] = lambda: mock_service

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.delete(
                f"/schedules/{uuid.uuid4()}/agendas/{uuid.uuid4()}"
            )

        assert response.status_code == 403

    async def test_no_auth_returns_401(self) -> None:
        app = _build_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.delete(
                f"/schedules/{uuid.uuid4()}/agendas/{uuid.uuid4()}"
            )

        assert response.status_code == 401


# -----------------------------------------------------------------------
# POST /agendas/{agenda_id}/comments
# -----------------------------------------------------------------------


class TestAddAgendaComment:
    """Tests for POST /agendas/{agenda_id}/comments."""

    async def test_success_returns_201(self) -> None:
        comment_id = CommentId.generate()
        mock_service = AsyncMock(spec=AddAgendaCommentService)
        mock_service.execute.return_value = AddAgendaCommentOutput(
            comment_id=comment_id
        )

        app = _build_app()
        _override_auth(app)
        app.dependency_overrides[get_add_agenda_comment_service] = lambda: mock_service

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                f"/agendas/{uuid.uuid4()}/comments",
                json={"body": "Looking forward to discussing this."},
            )

        assert response.status_code == 201
        assert response.json()["comment_id"] == str(comment_id.value)

    async def test_agenda_not_found_returns_404(self) -> None:
        agenda_id = AgendaId.generate()
        mock_service = AsyncMock(spec=AddAgendaCommentService)
        mock_service.execute.side_effect = AgendaCommentAgendaNotFoundError(agenda_id)

        app = _build_app()
        _override_auth(app)
        app.dependency_overrides[get_add_agenda_comment_service] = lambda: mock_service

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                f"/agendas/{agenda_id.value}/comments",
                json={"body": "Test comment"},
            )

        assert response.status_code == 404

    async def test_unauthorized_returns_403(self) -> None:
        mock_service = AsyncMock(spec=AddAgendaCommentService)
        mock_service.execute.side_effect = UnauthorizedAgendaCommentError()

        app = _build_app()
        _override_auth(app)
        app.dependency_overrides[get_add_agenda_comment_service] = lambda: mock_service

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                f"/agendas/{uuid.uuid4()}/comments",
                json={"body": "Test comment"},
            )

        assert response.status_code == 403

    async def test_no_auth_returns_401(self) -> None:
        app = _build_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                f"/agendas/{uuid.uuid4()}/comments",
                json={"body": "Test comment"},
            )

        assert response.status_code == 401


# -----------------------------------------------------------------------
# GET /records/last-summary
# -----------------------------------------------------------------------


class TestGetLastSessionSummary:
    """Tests for GET /records/last-summary."""

    async def test_success_returns_200(self) -> None:
        record_id = RecordId.generate()
        now = datetime.now(UTC)
        action_item_id = ActionItemId.generate()
        mock_service = AsyncMock(spec=GetLastSessionSummaryQueryService)
        mock_service.execute.return_value = GetLastSessionSummaryOutput(
            record_id=record_id,
            conducted_at=now,
            memo_excerpt="Summary of last session...",
            action_items=[
                ActionItemSummaryDTO(
                    action_item_id=action_item_id,
                    content="Follow up on project plan",
                    is_completed=False,
                    created_at=now,
                ),
            ],
        )

        app = _build_app()
        _override_auth(app)
        app.dependency_overrides[get_get_last_session_summary_service] = lambda: (
            mock_service
        )

        organizer_id = str(ACTOR_ID.value)
        counterpart_id = str(COUNTERPART_ID)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                "/records/last-summary",
                params={
                    "organizer_id": organizer_id,
                    "counterpart_id": counterpart_id,
                },
            )

        assert response.status_code == 200
        body = response.json()
        assert body["record_id"] == str(record_id.value)
        assert body["memo_excerpt"] == "Summary of last session..."
        assert len(body["action_items"]) == 1

    async def test_no_record_returns_200_null(self) -> None:
        mock_service = AsyncMock(spec=GetLastSessionSummaryQueryService)
        mock_service.execute.return_value = None

        app = _build_app()
        _override_auth(app)
        app.dependency_overrides[get_get_last_session_summary_service] = lambda: (
            mock_service
        )

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                "/records/last-summary",
                params={
                    "organizer_id": str(uuid.uuid4()),
                    "counterpart_id": str(uuid.uuid4()),
                },
            )

        assert response.status_code == 200
        assert response.json() is None

    async def test_no_auth_returns_401(self) -> None:
        app = _build_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                "/records/last-summary",
                params={
                    "organizer_id": str(uuid.uuid4()),
                    "counterpart_id": str(uuid.uuid4()),
                },
            )

        assert response.status_code == 401


# -----------------------------------------------------------------------
# GET /templates
# -----------------------------------------------------------------------


class TestListTemplates:
    """Tests for GET /templates."""

    async def test_success_returns_200(self) -> None:
        template_id = TemplateId.generate()
        now = datetime.now(UTC)
        mock_service = AsyncMock(spec=ListTemplatesService)
        mock_service.execute.return_value = ListTemplatesOutput(
            templates=[
                TemplateListItem(
                    template_id=template_id,
                    name="My template",
                    default_counterpart_ids=[
                        UserId(value=COUNTERPART_ID),
                    ],
                    agenda_topics=["Topic 1"],
                    created_at=now,
                    updated_at=now,
                ),
            ],
        )

        app = _build_app()
        _override_auth(app)
        app.dependency_overrides[get_list_templates_service] = lambda: mock_service

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/templates")

        assert response.status_code == 200
        body = response.json()
        assert len(body["templates"]) == 1
        assert body["templates"][0]["template_id"] == str(template_id.value)
        assert body["templates"][0]["name"] == "My template"

    async def test_no_auth_returns_401(self) -> None:
        app = _build_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/templates")

        assert response.status_code == 401


# -----------------------------------------------------------------------
# GET /templates/{template_id}
# -----------------------------------------------------------------------


class TestGetTemplate:
    """Tests for GET /templates/{template_id}."""

    async def test_success_returns_200(self) -> None:
        template_id = TemplateId.generate()
        now = datetime.now(UTC)
        mock_service = AsyncMock(spec=GetTemplateService)
        mock_service.execute.return_value = GetTemplateOutput(
            template_id=template_id,
            organizer_id=ACTOR_ID,
            name="My template",
            default_counterpart_ids=[UserId(value=COUNTERPART_ID)],
            agenda_topics=["Topic 1"],
            created_at=now,
            updated_at=now,
        )

        app = _build_app()
        _override_auth(app)
        app.dependency_overrides[get_get_template_service] = lambda: mock_service

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                f"/templates/{template_id.value}",
            )

        assert response.status_code == 200
        body = response.json()
        assert body["template_id"] == str(template_id.value)
        assert body["organizer_id"] == str(ACTOR_ID.value)
        assert body["name"] == "My template"

    async def test_not_found_returns_404(self) -> None:
        mock_service = AsyncMock(spec=GetTemplateService)
        mock_service.execute.side_effect = TemplateNotFoundError()

        app = _build_app()
        _override_auth(app)
        app.dependency_overrides[get_get_template_service] = lambda: mock_service

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                f"/templates/{uuid.uuid4()}",
            )

        assert response.status_code == 404

    async def test_unauthorized_access_returns_403(self) -> None:
        mock_service = AsyncMock(spec=GetTemplateService)
        mock_service.execute.side_effect = UnauthorizedTemplateAccessError()

        app = _build_app()
        _override_auth(app)
        app.dependency_overrides[get_get_template_service] = lambda: mock_service

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                f"/templates/{uuid.uuid4()}",
            )

        assert response.status_code == 403

    async def test_no_auth_returns_401(self) -> None:
        app = _build_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                f"/templates/{uuid.uuid4()}",
            )

        assert response.status_code == 401


# -----------------------------------------------------------------------
# POST /templates
# -----------------------------------------------------------------------


class TestSaveTemplate:
    """Tests for POST /templates."""

    async def test_success_returns_201(self) -> None:
        template_id = TemplateId.generate()
        mock_service = AsyncMock(spec=SaveTemplateService)
        mock_service.execute.return_value = SaveTemplateOutput(
            template_id=template_id,
        )

        app = _build_app()
        _override_auth(app)
        app.dependency_overrides[get_save_template_service] = lambda: mock_service

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/templates",
                json={
                    "name": "My template",
                    "default_counterpart_ids": [str(COUNTERPART_ID)],
                    "agenda_topics": ["Topic 1"],
                },
            )

        assert response.status_code == 201
        assert response.json()["template_id"] == str(template_id.value)

    async def test_no_auth_returns_401(self) -> None:
        app = _build_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/templates",
                json={
                    "name": "My template",
                    "default_counterpart_ids": [],
                    "agenda_topics": [],
                },
            )

        assert response.status_code == 401
