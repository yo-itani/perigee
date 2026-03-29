"""Integration tests for Preparation context API endpoints.

These tests exercise the full HTTP layer (router -> DI -> use case -> repository -> DB)
using the real FastAPI app with httpx.AsyncClient.  No DI overrides are used.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from api.event_setup import create_event_dispatcher
from api.exception_handlers import register_exception_handlers
from api.register_routers import register_routers
from shared.domain.value_objects import UserId
from tests.helpers import auth_headers, create_test_user

pytestmark = pytest.mark.integration

_BASE_URL = "http://test"


def _future(days: int = 30) -> str:
    """Return an ISO 8601 timestamp ``days`` into the future (UTC)."""
    return (datetime.now(UTC) + timedelta(days=days)).isoformat()


async def _new_user(session_factory: async_sessionmaker[AsyncSession]) -> str:
    """Create a new random user in the DB and return its id string."""
    uid = str(uuid.uuid4())
    async with session_factory() as s:
        await create_test_user(s, user_id=UserId(uuid.UUID(uid)))
        await s.commit()
    return uid


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
async def user_id(session_factory: async_sessionmaker[AsyncSession]) -> str:
    return await _new_user(session_factory)


class TestCreateScheduleGroupAuth:
    """POST /schedule-groups -- authentication checks."""

    async def test_returns_401_without_auth_header(self, app) -> None:
        """Request without Authorization header returns 401."""
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
        """Request without Authorization header returns 401."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            response = await client.post(
                "/schedules",
                json={
                    "counterpart_id": str(uuid.uuid4()),
                    "scheduled_at": _future(30),
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
                headers=auth_headers(user_id),
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
                headers=auth_headers(user_id),
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
        """Request without Authorization header returns 401."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            response = await client.post(
                "/schedules/consultation-request",
                json={
                    "organizer_id": str(uuid.uuid4()),
                    "scheduled_at": _future(30),
                    "title": "Consultation",
                    "agenda_topics": ["Topic 1"],
                },
            )

        assert response.status_code == 401


# =====================================================================
# Schedule group creation -- POST /schedule-groups
# =====================================================================


class TestCreateScheduleGroup:
    """POST /schedule-groups -- group creation with DB verification."""

    async def test_creates_group_and_schedules_in_db(
        self, app, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """Creating a schedule group persists schedule_groups + schedules rows."""
        organizer_id = await _new_user(session_factory)
        cp_id = await _new_user(session_factory)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            response = await client.post(
                "/schedule-groups",
                headers=auth_headers(organizer_id),
                json={
                    "title": "Weekly 1on1",
                    "counterpart_schedules": [
                        {
                            "counterpart_id": cp_id,
                            "scheduled_at": _future(30),
                        },
                    ],
                    "agenda_topics": ["Progress", "Blockers"],
                },
            )

        assert response.status_code == 201
        data = response.json()
        group_id = data["schedule_group_id"]
        uuid.UUID(group_id)  # validates UUID format

        # Verify schedule_groups row
        async with session_factory() as s:
            from contexts.preparation.infrastructure.tables import (
                ScheduleGroupAgendaTemplateTable,
                ScheduleGroupTable,
                ScheduleTable,
            )

            result = await s.execute(
                select(ScheduleGroupTable).where(ScheduleGroupTable.id == group_id)
            )
            group_row = result.scalar_one()
            assert group_row.organizer_id == organizer_id
            assert group_row.title == "Weekly 1on1"

            # Verify schedules row
            result = await s.execute(
                select(ScheduleTable).where(
                    ScheduleTable.schedule_group_id == group_id
                )
            )
            schedule_rows = result.scalars().all()
            assert len(schedule_rows) == 1
            assert schedule_rows[0].counterpart_id == cp_id
            assert schedule_rows[0].organizer_id == organizer_id
            assert schedule_rows[0].status == "requested"

            # Verify agenda templates on the group
            result = await s.execute(
                select(ScheduleGroupAgendaTemplateTable).where(
                    ScheduleGroupAgendaTemplateTable.schedule_group_id == group_id
                )
            )
            agenda_rows = result.scalars().all()
            topics = sorted(r.topic for r in agenda_rows)
            assert topics == ["Blockers", "Progress"]


# =====================================================================
# Schedule group from template -- POST /schedule-groups/from-template
# =====================================================================


class TestCreateScheduleGroupFromTemplate:
    """POST /schedule-groups/from-template -- template agenda duplication."""

    async def test_creates_group_with_template_agendas_duplicated(
        self, app, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """Creating from template duplicates the template's agenda topics."""
        organizer_id = await _new_user(session_factory)
        cp_id = await _new_user(session_factory)

        # First create a template via API
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            tmpl_resp = await client.post(
                "/templates",
                headers=auth_headers(organizer_id),
                json={
                    "name": "Template A",
                    "default_counterpart_ids": [],
                    "agenda_topics": ["Topic X", "Topic Y"],
                },
            )
        assert tmpl_resp.status_code == 201
        template_id = tmpl_resp.json()["template_id"]

        # Create group from template
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            response = await client.post(
                "/schedule-groups/from-template",
                headers=auth_headers(organizer_id),
                json={
                    "template_id": template_id,
                    "title": "From Template",
                    "counterpart_schedules": [
                        {
                            "counterpart_id": cp_id,
                            "scheduled_at": _future(30),
                        },
                    ],
                },
            )

        assert response.status_code == 201
        group_id = response.json()["schedule_group_id"]

        # Verify agenda templates are duplicated from template
        async with session_factory() as s:
            from contexts.preparation.infrastructure.tables import (
                ScheduleGroupAgendaTemplateTable,
                ScheduleGroupTable,
            )

            result = await s.execute(
                select(ScheduleGroupTable).where(ScheduleGroupTable.id == group_id)
            )
            group_row = result.scalar_one()
            assert group_row.template_id == template_id

            result = await s.execute(
                select(ScheduleGroupAgendaTemplateTable).where(
                    ScheduleGroupAgendaTemplateTable.schedule_group_id == group_id
                )
            )
            agenda_rows = result.scalars().all()
            topics = sorted(r.topic for r in agenda_rows)
            assert topics == ["Topic X", "Topic Y"]


# =====================================================================
# Schedule group from past -- POST /schedule-groups/from-past
# =====================================================================


class TestCreateScheduleGroupFromPast:
    """POST /schedule-groups/from-past -- past group settings carried over."""

    async def test_creates_group_inheriting_past_group_settings(
        self, app, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """Creating from past carries over agenda topics from the source group."""
        organizer_id = await _new_user(session_factory)
        cp_id = await _new_user(session_factory)

        transport = ASGITransport(app=app)

        # Create original group with agendas
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            orig_resp = await client.post(
                "/schedule-groups",
                headers=auth_headers(organizer_id),
                json={
                    "title": "Original Group",
                    "counterpart_schedules": [
                        {
                            "counterpart_id": cp_id,
                            "scheduled_at": _future(30),
                        },
                    ],
                    "agenda_topics": ["Carry A", "Carry B"],
                },
            )
        assert orig_resp.status_code == 201
        source_group_id = orig_resp.json()["schedule_group_id"]

        # Create from past
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            response = await client.post(
                "/schedule-groups/from-past",
                headers=auth_headers(organizer_id),
                json={
                    "source_schedule_group_id": source_group_id,
                    "title": "Follow-up Group",
                    "counterpart_schedules": [
                        {
                            "counterpart_id": cp_id,
                            "scheduled_at": _future(60),
                        },
                    ],
                },
            )

        assert response.status_code == 201
        new_group_id = response.json()["schedule_group_id"]
        assert new_group_id != source_group_id

        # Verify agenda topics were inherited
        async with session_factory() as s:
            from contexts.preparation.infrastructure.tables import (
                ScheduleGroupAgendaTemplateTable,
            )

            result = await s.execute(
                select(ScheduleGroupAgendaTemplateTable).where(
                    ScheduleGroupAgendaTemplateTable.schedule_group_id == new_group_id
                )
            )
            agenda_rows = result.scalars().all()
            topics = sorted(r.topic for r in agenda_rows)
            assert topics == ["Carry A", "Carry B"]


# =====================================================================
# Single schedule creation -- POST /schedules
# =====================================================================


class TestCreateSchedule:
    """POST /schedules -- single schedule creation with DB verification."""

    async def test_creates_schedule_in_db(
        self, app, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """Creating a schedule persists a schedule row in the DB."""
        organizer_id = await _new_user(session_factory)
        cp_id = await _new_user(session_factory)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            response = await client.post(
                "/schedules",
                headers=auth_headers(organizer_id),
                json={
                    "counterpart_id": cp_id,
                    "scheduled_at": _future(30),
                    "title": "Ad-hoc 1on1",
                },
            )

        assert response.status_code == 201
        schedule_id = response.json()["schedule_id"]
        uuid.UUID(schedule_id)

        async with session_factory() as s:
            from contexts.preparation.infrastructure.tables import ScheduleTable

            result = await s.execute(
                select(ScheduleTable).where(ScheduleTable.id == schedule_id)
            )
            row = result.scalar_one()
            assert row.organizer_id == organizer_id
            assert row.counterpart_id == cp_id
            assert row.title == "Ad-hoc 1on1"
            assert row.status == "requested"
            assert row.schedule_group_id is None


# =====================================================================
# Upcoming schedules -- GET /schedules/upcoming
# =====================================================================


class TestListUpcomingSchedules:
    """GET /schedules/upcoming -- filtering verification."""

    async def test_returns_future_non_cancelled_schedules(
        self, app, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """Upcoming list includes future REQUESTED/CONFIRMED, excludes cancelled."""
        organizer_id = await _new_user(session_factory)
        cp_id = await _new_user(session_factory)

        transport = ASGITransport(app=app)

        # Create two schedules via API (both future, status=requested)
        schedule_ids = []
        for i, date in enumerate(
            [_future(30), _future(31)]
        ):
            async with AsyncClient(
                transport=transport, base_url=_BASE_URL
            ) as client:
                resp = await client.post(
                    "/schedules",
                    headers=auth_headers(organizer_id),
                    json={
                        "counterpart_id": cp_id,
                        "scheduled_at": date,
                        "title": f"Meeting {i}",
                    },
                )
            assert resp.status_code == 201
            schedule_ids.append(resp.json()["schedule_id"])

        # Cancel the second schedule
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            cancel_resp = await client.post(
                f"/schedules/{schedule_ids[1]}/cancel",
                headers=auth_headers(organizer_id),
            )
        assert cancel_resp.status_code == 204

        # Fetch upcoming
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            response = await client.get(
                "/schedules/upcoming",
                headers=auth_headers(organizer_id),
            )

        assert response.status_code == 200
        returned_ids = [s["schedule_id"] for s in response.json()["schedules"]]
        assert schedule_ids[0] in returned_ids
        assert schedule_ids[1] not in returned_ids

    async def test_excludes_other_users_schedules(
        self, app, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """Upcoming list does not contain schedules of unrelated users."""
        user_a = await _new_user(session_factory)
        user_b = await _new_user(session_factory)
        cp = await _new_user(session_factory)

        transport = ASGITransport(app=app)

        # User A creates a schedule
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            resp = await client.post(
                "/schedules",
                headers=auth_headers(user_a),
                json={
                    "counterpart_id": cp,
                    "scheduled_at": _future(30),
                    "title": "A's meeting",
                },
            )
        assert resp.status_code == 201
        a_schedule_id = resp.json()["schedule_id"]

        # User B queries upcoming -- should NOT see user A's schedule
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            response = await client.get(
                "/schedules/upcoming",
                headers=auth_headers(user_b),
            )

        assert response.status_code == 200
        returned_ids = [s["schedule_id"] for s in response.json()["schedules"]]
        assert a_schedule_id not in returned_ids


# =====================================================================
# Schedule detail -- GET /schedules/{schedule_id}
# =====================================================================


class TestGetScheduleDetail:
    """GET /schedules/{schedule_id} -- detail retrieval."""

    async def test_returns_schedule_detail(
        self, app, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """Detail endpoint returns fields matching the DB state."""
        organizer_id = await _new_user(session_factory)
        cp_id = await _new_user(session_factory)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            create_resp = await client.post(
                "/schedules",
                headers=auth_headers(organizer_id),
                json={
                    "counterpart_id": cp_id,
                    "scheduled_at": _future(30),
                    "title": "Detail check",
                },
            )
        assert create_resp.status_code == 201
        schedule_id = create_resp.json()["schedule_id"]

        # Fetch detail
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            response = await client.get(
                f"/schedules/{schedule_id}",
                headers=auth_headers(organizer_id),
            )

        assert response.status_code == 200
        detail = response.json()
        assert detail["schedule_id"] == schedule_id
        assert detail["organizer_id"] == organizer_id
        assert detail["counterpart_id"] == cp_id
        assert detail["title"] == "Detail check"
        assert detail["status"] == "requested"
        assert detail["schedule_group_id"] is None

    async def test_counterpart_can_view_detail(
        self, app, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """The counterpart of a schedule can also view its detail."""
        organizer_id = await _new_user(session_factory)
        cp_id = await _new_user(session_factory)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            create_resp = await client.post(
                "/schedules",
                headers=auth_headers(organizer_id),
                json={
                    "counterpart_id": cp_id,
                    "scheduled_at": _future(30),
                    "title": "CP view test",
                },
            )
        assert create_resp.status_code == 201
        schedule_id = create_resp.json()["schedule_id"]

        # Counterpart fetches detail
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            response = await client.get(
                f"/schedules/{schedule_id}",
                headers=auth_headers(cp_id),
            )

        assert response.status_code == 200
        assert response.json()["schedule_id"] == schedule_id

    async def test_unrelated_user_cannot_view_detail(
        self, app, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """An unrelated user receives 403 when viewing another's schedule."""
        organizer_id = await _new_user(session_factory)
        cp_id = await _new_user(session_factory)
        stranger = await _new_user(session_factory)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            create_resp = await client.post(
                "/schedules",
                headers=auth_headers(organizer_id),
                json={
                    "counterpart_id": cp_id,
                    "scheduled_at": _future(30),
                    "title": "Private meeting",
                },
            )
        assert create_resp.status_code == 201
        schedule_id = create_resp.json()["schedule_id"]

        # Stranger tries to view
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            response = await client.get(
                f"/schedules/{schedule_id}",
                headers=auth_headers(stranger),
            )

        assert response.status_code == 403


# =====================================================================
# Agenda management -- POST / GET / DELETE agendas
# =====================================================================


class TestAddAgenda:
    """POST /schedules/{schedule_id}/agendas -- agenda creation."""

    async def test_adds_agenda_and_returns_201(
        self, app, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """Adding an agenda returns 201 and persists the row in the DB."""
        organizer_id = await _new_user(session_factory)
        cp_id = await _new_user(session_factory)

        transport = ASGITransport(app=app)

        # Create a schedule first
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            sched_resp = await client.post(
                "/schedules",
                headers=auth_headers(organizer_id),
                json={
                    "counterpart_id": cp_id,
                    "scheduled_at": _future(30),
                    "title": "Agenda test",
                },
            )
        assert sched_resp.status_code == 201
        schedule_id = sched_resp.json()["schedule_id"]

        # Add agenda
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            response = await client.post(
                f"/schedules/{schedule_id}/agendas",
                headers=auth_headers(organizer_id),
                json={"topic": "Discuss project timeline"},
            )

        assert response.status_code == 201
        agenda_id = response.json()["agenda_id"]
        uuid.UUID(agenda_id)

        # Verify DB
        async with session_factory() as s:
            from contexts.preparation.infrastructure.tables import AgendaTable

            result = await s.execute(
                select(AgendaTable).where(AgendaTable.id == agenda_id)
            )
            row = result.scalar_one()
            assert row.topic == "Discuss project timeline"
            assert row.schedule_id == schedule_id
            assert row.added_by == organizer_id


class TestListScheduleAgendas:
    """GET /schedules/{schedule_id}/agendas -- agenda listing."""

    async def test_returns_agendas_for_schedule(
        self, app, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """Listing agendas returns previously added agendas."""
        organizer_id = await _new_user(session_factory)
        cp_id = await _new_user(session_factory)

        transport = ASGITransport(app=app)

        # Create schedule
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            sched_resp = await client.post(
                "/schedules",
                headers=auth_headers(organizer_id),
                json={
                    "counterpart_id": cp_id,
                    "scheduled_at": _future(30),
                    "title": "List agenda test",
                },
            )
        assert sched_resp.status_code == 201
        schedule_id = sched_resp.json()["schedule_id"]

        # Add two agendas
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            resp1 = await client.post(
                f"/schedules/{schedule_id}/agendas",
                headers=auth_headers(organizer_id),
                json={"topic": "Topic A"},
            )
            resp2 = await client.post(
                f"/schedules/{schedule_id}/agendas",
                headers=auth_headers(organizer_id),
                json={"topic": "Topic B"},
            )
        assert resp1.status_code == 201
        assert resp2.status_code == 201

        # List agendas
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            response = await client.get(
                f"/schedules/{schedule_id}/agendas",
                headers=auth_headers(organizer_id),
            )

        assert response.status_code == 200
        agendas = response.json()["agendas"]
        topics = sorted(a["topic"] for a in agendas)
        assert topics == ["Topic A", "Topic B"]

    async def test_returns_empty_list_when_no_agendas(
        self, app, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """A schedule with no agendas returns an empty list."""
        organizer_id = await _new_user(session_factory)
        cp_id = await _new_user(session_factory)

        transport = ASGITransport(app=app)

        # Create schedule without agendas
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            sched_resp = await client.post(
                "/schedules",
                headers=auth_headers(organizer_id),
                json={
                    "counterpart_id": cp_id,
                    "scheduled_at": _future(30),
                    "title": "Empty agenda test",
                },
            )
        assert sched_resp.status_code == 201
        schedule_id = sched_resp.json()["schedule_id"]

        # List agendas
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            response = await client.get(
                f"/schedules/{schedule_id}/agendas",
                headers=auth_headers(organizer_id),
            )

        assert response.status_code == 200
        assert response.json()["agendas"] == []


class TestDeleteAgenda:
    """DELETE /schedules/{schedule_id}/agendas/{agenda_id} -- agenda deletion."""

    async def test_deletes_agenda_and_returns_204(
        self, app, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """Deleting an agenda returns 204 and removes the row from DB."""
        organizer_id = await _new_user(session_factory)
        cp_id = await _new_user(session_factory)

        transport = ASGITransport(app=app)

        # Create schedule
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            sched_resp = await client.post(
                "/schedules",
                headers=auth_headers(organizer_id),
                json={
                    "counterpart_id": cp_id,
                    "scheduled_at": _future(30),
                    "title": "Delete agenda test",
                },
            )
        assert sched_resp.status_code == 201
        schedule_id = sched_resp.json()["schedule_id"]

        # Add agenda
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            add_resp = await client.post(
                f"/schedules/{schedule_id}/agendas",
                headers=auth_headers(organizer_id),
                json={"topic": "To be deleted"},
            )
        assert add_resp.status_code == 201
        agenda_id = add_resp.json()["agenda_id"]

        # Delete agenda
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            response = await client.delete(
                f"/schedules/{schedule_id}/agendas/{agenda_id}",
                headers=auth_headers(organizer_id),
            )

        assert response.status_code == 204

        # Verify DB: row is gone
        async with session_factory() as s:
            from contexts.preparation.infrastructure.tables import AgendaTable

            result = await s.execute(
                select(AgendaTable).where(AgendaTable.id == agenda_id)
            )
            assert result.scalar_one_or_none() is None


# =====================================================================
# Agenda comments -- POST /agendas/{agenda_id}/comments
# =====================================================================


class TestAddAgendaComment:
    """POST /agendas/{agenda_id}/comments -- comment creation."""

    async def test_adds_comment_and_returns_201(
        self, app, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """Adding a comment returns 201 and persists the row in agenda_comments."""
        organizer_id = await _new_user(session_factory)
        cp_id = await _new_user(session_factory)

        transport = ASGITransport(app=app)

        # Create schedule
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            sched_resp = await client.post(
                "/schedules",
                headers=auth_headers(organizer_id),
                json={
                    "counterpart_id": cp_id,
                    "scheduled_at": _future(30),
                    "title": "Comment test",
                },
            )
        assert sched_resp.status_code == 201
        schedule_id = sched_resp.json()["schedule_id"]

        # Add agenda
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            agenda_resp = await client.post(
                f"/schedules/{schedule_id}/agendas",
                headers=auth_headers(organizer_id),
                json={"topic": "Discussion point"},
            )
        assert agenda_resp.status_code == 201
        agenda_id = agenda_resp.json()["agenda_id"]

        # Add comment
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            response = await client.post(
                f"/agendas/{agenda_id}/comments",
                headers=auth_headers(organizer_id),
                json={"body": "Let's discuss this first"},
            )

        assert response.status_code == 201
        comment_id = response.json()["comment_id"]
        uuid.UUID(comment_id)

        # Verify DB
        async with session_factory() as s:
            from contexts.preparation.infrastructure.tables import AgendaCommentTable

            result = await s.execute(
                select(AgendaCommentTable).where(AgendaCommentTable.id == comment_id)
            )
            row = result.scalar_one()
            assert row.agenda_id == agenda_id
            assert row.author_id == organizer_id
            assert row.body == "Let's discuss this first"


# =====================================================================
# Template detail -- GET /templates/{template_id}
# =====================================================================


class TestGetTemplate:
    """GET /templates/{template_id} -- template detail retrieval."""

    async def test_returns_template_detail(
        self, app, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """Getting a template returns its full details matching DB state."""
        organizer_id = await _new_user(session_factory)

        transport = ASGITransport(app=app)

        # Create a template
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            create_resp = await client.post(
                "/templates",
                headers=auth_headers(organizer_id),
                json={
                    "name": "Detail Template",
                    "default_counterpart_ids": [],
                    "agenda_topics": ["Review", "Planning"],
                },
            )
        assert create_resp.status_code == 201
        template_id = create_resp.json()["template_id"]

        # Get template detail
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            response = await client.get(
                f"/templates/{template_id}",
                headers=auth_headers(organizer_id),
            )

        assert response.status_code == 200
        detail = response.json()
        assert detail["template_id"] == template_id
        assert detail["organizer_id"] == organizer_id
        assert detail["name"] == "Detail Template"
        assert detail["default_counterpart_ids"] == []
        assert sorted(detail["agenda_topics"]) == ["Planning", "Review"]

    async def test_returns_404_for_nonexistent_template(
        self, app, user_id: str
    ) -> None:
        """Getting a nonexistent template returns 404."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            response = await client.get(
                f"/templates/{uuid.uuid4()}",
                headers=auth_headers(user_id),
            )

        assert response.status_code == 404


# =====================================================================
# Pending action items -- GET /action-items/pending
# =====================================================================


class TestListAllPendingActionItems:
    """GET /action-items/pending -- all pending action items."""

    async def test_returns_pending_action_items(
        self, app, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """Pending items from a published record are returned."""
        organizer_id = await _new_user(session_factory)
        cp_id = await _new_user(session_factory)

        transport = ASGITransport(app=app)

        # Create a record, add action item, then publish
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            rec_resp = await client.post(
                "/records/post-hoc",
                headers=auth_headers(organizer_id),
                json={
                    "counterpart_id": cp_id,
                    "conducted_at": _future(0),
                },
            )
        assert rec_resp.status_code == 201
        record_id = rec_resp.json()["record_id"]

        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            ai_resp = await client.post(
                f"/records/{record_id}/action-items",
                headers=auth_headers(organizer_id),
                json={"title": "Follow up on metrics"},
            )
        assert ai_resp.status_code == 201
        action_item_id = ai_resp.json()["action_item_id"]

        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            pub_resp = await client.post(
                f"/records/{record_id}/publish",
                headers=auth_headers(organizer_id),
                json={"viewer_ids": []},
            )
        assert pub_resp.status_code == 200

        # Query pending action items
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            response = await client.get(
                "/action-items/pending",
                headers=auth_headers(organizer_id),
            )

        assert response.status_code == 200
        items = response.json()["items"]
        returned_ids = [i["action_item_id"] for i in items]
        assert action_item_id in returned_ids

    async def test_returns_empty_list_when_no_items(
        self, app, user_id: str
    ) -> None:
        """A user with no action items gets an empty list."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            response = await client.get(
                "/action-items/pending",
                headers=auth_headers(user_id),
            )

        assert response.status_code == 200
        assert response.json()["items"] == []


# =====================================================================
# Pending action items by counterpart -- GET /action-items/pending/{id}
# =====================================================================


class TestListPendingActionItemsByCounterpart:
    """GET /action-items/pending/{counterpart_id} -- filtered by counterpart."""

    async def test_filters_by_counterpart(
        self, app, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """Only action items for the specified counterpart are returned."""
        organizer_id = await _new_user(session_factory)
        cp_a = await _new_user(session_factory)
        cp_b = await _new_user(session_factory)

        transport = ASGITransport(app=app)

        # Create record with cp_a and add action item
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            rec_a = await client.post(
                "/records/post-hoc",
                headers=auth_headers(organizer_id),
                json={"counterpart_id": cp_a, "conducted_at": _future(0)},
            )
        assert rec_a.status_code == 201
        record_a_id = rec_a.json()["record_id"]

        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            await client.post(
                f"/records/{record_a_id}/action-items",
                headers=auth_headers(organizer_id),
                json={"title": "Item for A"},
            )
            pub = await client.post(
                f"/records/{record_a_id}/publish",
                headers=auth_headers(organizer_id),
                json={"viewer_ids": []},
            )
        assert pub.status_code == 200

        # Create record with cp_b and add action item
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            rec_b = await client.post(
                "/records/post-hoc",
                headers=auth_headers(organizer_id),
                json={"counterpart_id": cp_b, "conducted_at": _future(0)},
            )
        assert rec_b.status_code == 201
        record_b_id = rec_b.json()["record_id"]

        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            await client.post(
                f"/records/{record_b_id}/action-items",
                headers=auth_headers(organizer_id),
                json={"title": "Item for B"},
            )
            pub = await client.post(
                f"/records/{record_b_id}/publish",
                headers=auth_headers(organizer_id),
                json={"viewer_ids": []},
            )
        assert pub.status_code == 200

        # Query pending for cp_a only
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            response = await client.get(
                f"/action-items/pending/{cp_a}",
                headers=auth_headers(organizer_id),
            )

        assert response.status_code == 200
        items = response.json()["items"]
        assert len(items) >= 1
        counterpart_ids = {i.get("counterpart_id") for i in items}
        # All returned items should NOT include cp_b's counterpart_id
        # (this endpoint returns organizer_id, not counterpart_id)
        titles = [i["content"] for i in items]
        assert "Item for A" in titles
        assert "Item for B" not in titles


# =====================================================================
# Last session summary -- GET /records/last-summary
# =====================================================================


class TestGetLastSessionSummary:
    """GET /records/last-summary -- last session summary."""

    async def test_returns_last_summary(
        self, app, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """Published record's summary is returned for the organizer-counterpart pair."""
        organizer_id = await _new_user(session_factory)
        cp_id = await _new_user(session_factory)

        transport = ASGITransport(app=app)

        # Create record, update memo, publish
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            rec_resp = await client.post(
                "/records/post-hoc",
                headers=auth_headers(organizer_id),
                json={
                    "counterpart_id": cp_id,
                    "conducted_at": _future(0),
                },
            )
        assert rec_resp.status_code == 201
        record_id = rec_resp.json()["record_id"]

        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            await client.put(
                f"/records/{record_id}/memo",
                headers=auth_headers(organizer_id),
                json={"memo": "Discussed quarterly goals"},
            )
            await client.post(
                f"/records/{record_id}/publish",
                headers=auth_headers(organizer_id),
                json={"viewer_ids": []},
            )

        # Query last summary
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            response = await client.get(
                "/records/last-summary",
                headers=auth_headers(organizer_id),
                params={
                    "organizer_id": organizer_id,
                    "counterpart_id": cp_id,
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data["record_id"] == record_id
        assert "Discussed quarterly goals" in data["memo_excerpt"]

    async def test_returns_null_when_no_records(
        self, app, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """Returns null when no published records exist for the pair."""
        organizer_id = await _new_user(session_factory)
        cp_id = await _new_user(session_factory)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            response = await client.get(
                "/records/last-summary",
                headers=auth_headers(organizer_id),
                params={
                    "organizer_id": organizer_id,
                    "counterpart_id": cp_id,
                },
            )

        assert response.status_code == 200
        assert response.json() is None
