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
from contexts.preparation.application.get_template_service import (
    GetTemplateOutput,
    GetTemplateService,
    TemplateNotFoundError,
    UnauthorizedTemplateAccessError,
)
from contexts.preparation.application.list_templates_service import (
    ListTemplatesOutput,
    ListTemplatesService,
    TemplateListItem,
)
from contexts.preparation.application.save_template_service import (
    SaveTemplateOutput,
    SaveTemplateService,
)
from contexts.preparation.application.send_consultation_request_service import (
    SendConsultationRequestOutput,
    SendConsultationRequestService,
)
from contexts.preparation.domain.value_objects import (
    ScheduleGroupId,
    ScheduleId,
    TemplateId,
)
from contexts.preparation.presentation.dependencies import (
    get_create_schedule_group_from_past_service,
    get_create_schedule_group_from_template_service,
    get_create_schedule_group_service,
    get_create_schedule_service,
    get_get_template_service,
    get_list_templates_service,
    get_save_template_service,
    get_send_consultation_request_service,
)
from contexts.preparation.presentation.router import router
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
        app.dependency_overrides[get_create_schedule_group_service] = (
            lambda: mock_service
        )

        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
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
        async with AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
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
        mock_service.execute.return_value = (
            CreateScheduleGroupFromTemplateOutput(schedule_group_id=group_id)
        )

        app = _build_app()
        _override_auth(app)
        app.dependency_overrides[
            get_create_schedule_group_from_template_service
        ] = lambda: mock_service

        template_id = str(uuid.uuid4())
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
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
        async with AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
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
        mock_service.execute.return_value = (
            CreateScheduleGroupFromPastOutput(schedule_group_id=group_id)
        )

        app = _build_app()
        _override_auth(app)
        app.dependency_overrides[
            get_create_schedule_group_from_past_service
        ] = lambda: mock_service

        source_id = str(uuid.uuid4())
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
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
        async with AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
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
        app.dependency_overrides[get_create_schedule_service] = (
            lambda: mock_service
        )

        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
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
        async with AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
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
        app.dependency_overrides[get_send_consultation_request_service] = (
            lambda: mock_service
        )

        organizer_id = str(uuid.uuid4())
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
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
        async with AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
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
        app.dependency_overrides[get_list_templates_service] = (
            lambda: mock_service
        )

        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            response = await client.get("/templates")

        assert response.status_code == 200
        body = response.json()
        assert len(body["templates"]) == 1
        assert body["templates"][0]["template_id"] == str(template_id.value)
        assert body["templates"][0]["name"] == "My template"

    async def test_no_auth_returns_401(self) -> None:
        app = _build_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
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
        app.dependency_overrides[get_get_template_service] = (
            lambda: mock_service
        )

        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
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
        app.dependency_overrides[get_get_template_service] = (
            lambda: mock_service
        )

        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            response = await client.get(
                f"/templates/{uuid.uuid4()}",
            )

        assert response.status_code == 404

    async def test_unauthorized_access_returns_403(self) -> None:
        mock_service = AsyncMock(spec=GetTemplateService)
        mock_service.execute.side_effect = UnauthorizedTemplateAccessError()

        app = _build_app()
        _override_auth(app)
        app.dependency_overrides[get_get_template_service] = (
            lambda: mock_service
        )

        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            response = await client.get(
                f"/templates/{uuid.uuid4()}",
            )

        assert response.status_code == 403

    async def test_no_auth_returns_401(self) -> None:
        app = _build_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
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
        app.dependency_overrides[get_save_template_service] = (
            lambda: mock_service
        )

        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
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
        async with AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            response = await client.post(
                "/templates",
                json={
                    "name": "My template",
                    "default_counterpart_ids": [],
                    "agenda_topics": [],
                },
            )

        assert response.status_code == 401
