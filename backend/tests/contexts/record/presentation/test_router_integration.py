"""Integration tests for Record context API endpoints.

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


class TestCreatePostHocRecordAuth:
    """POST /records/post-hoc -- authentication checks."""

    async def test_returns_401_without_auth_header(self, app) -> None:
        """Request without Authorization header returns 401."""
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

    async def test_creates_record_and_returns_201(
        self,
        app,
        user_id: str,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        """An authenticated user can create a post-hoc record."""
        counterpart_id = await _new_user(session_factory)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            response = await client.post(
                "/records/post-hoc",
                headers=auth_headers(user_id),
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


# -----------------------------------------------------------------------
# GET /records/{id}/suggested-viewers
# -----------------------------------------------------------------------


class TestSuggestedViewersAuth:
    """GET /records/{id}/suggested-viewers -- authentication checks."""

    async def test_returns_401_without_auth_header(self, app) -> None:
        """Request without Authorization header returns 401."""
        record_id = str(uuid.uuid4())
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            response = await client.get(
                f"/records/{record_id}/suggested-viewers",
            )

        assert response.status_code == 401


class TestSuggestedViewers:
    """GET /records/{id}/suggested-viewers -- authenticated access."""

    async def test_returns_404_for_nonexistent_record(self, app, user_id: str) -> None:
        """Requesting suggested viewers for a nonexistent record returns 404."""
        record_id = str(uuid.uuid4())
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            response = await client.get(
                f"/records/{record_id}/suggested-viewers",
                headers=auth_headers(user_id),
            )

        assert response.status_code == 404

    async def test_returns_suggestions_for_existing_record(
        self,
        app,
        user_id: str,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        """Organizer can get suggested viewers for an existing record."""
        counterpart_id = await _new_user(session_factory)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            # First create a record
            create_response = await client.post(
                "/records/post-hoc",
                headers=auth_headers(user_id),
                json={
                    "counterpart_id": counterpart_id,
                    "conducted_at": "2026-03-20T14:00:00+09:00",
                },
            )
            record_id = create_response.json()["record_id"]

            # Then get suggested viewers
            response = await client.get(
                f"/records/{record_id}/suggested-viewers",
                headers=auth_headers(user_id),
            )

        assert response.status_code == 200
        data = response.json()
        assert "suggested_viewer_ids" in data
        assert isinstance(data["suggested_viewer_ids"], list)


# -----------------------------------------------------------------------
# PUT /records/{id}/viewers
# -----------------------------------------------------------------------


class TestSetViewersAuth:
    """PUT /records/{id}/viewers -- authentication checks."""

    async def test_returns_401_without_auth_header(self, app) -> None:
        """Request without Authorization header returns 401."""
        record_id = str(uuid.uuid4())
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            response = await client.put(
                f"/records/{record_id}/viewers",
                json={"viewer_ids": []},
            )

        assert response.status_code == 401


class TestSetViewersIntegration:
    """PUT /records/{id}/viewers -- authenticated access."""

    async def test_returns_404_for_nonexistent_record(self, app, user_id: str) -> None:
        """Setting viewers for a nonexistent record returns 404."""
        record_id = str(uuid.uuid4())
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            response = await client.put(
                f"/records/{record_id}/viewers",
                headers=auth_headers(user_id),
                json={"viewer_ids": [str(uuid.uuid4())]},
            )

        assert response.status_code == 404

    async def test_sets_viewers_for_existing_record(
        self,
        app,
        user_id: str,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        """Organizer can set viewers for an existing record."""
        viewer_id = await _new_user(session_factory)
        counterpart_id = await _new_user(session_factory)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            # First create a record
            create_response = await client.post(
                "/records/post-hoc",
                headers=auth_headers(user_id),
                json={
                    "counterpart_id": counterpart_id,
                    "conducted_at": "2026-03-20T14:00:00+09:00",
                },
            )
            record_id = create_response.json()["record_id"]

            # Then set viewers
            response = await client.put(
                f"/records/{record_id}/viewers",
                headers=auth_headers(user_id),
                json={"viewer_ids": [viewer_id]},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["record_id"] == record_id


# -----------------------------------------------------------------------
# POST /records/{id}/publish
# -----------------------------------------------------------------------


class TestPublishRecordAuth:
    """POST /records/{id}/publish -- authentication checks."""

    async def test_returns_401_without_auth_header(self, app) -> None:
        """Request without Authorization header returns 401."""
        record_id = str(uuid.uuid4())
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            response = await client.post(
                f"/records/{record_id}/publish",
                json={"viewer_ids": []},
            )

        assert response.status_code == 401


class TestPublishRecordIntegration:
    """POST /records/{id}/publish -- authenticated access."""

    async def test_returns_404_for_nonexistent_record(self, app, user_id: str) -> None:
        """Publishing a nonexistent record returns 404."""
        record_id = str(uuid.uuid4())
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            response = await client.post(
                f"/records/{record_id}/publish",
                headers=auth_headers(user_id),
                json={"viewer_ids": []},
            )

        assert response.status_code == 404

    async def test_publishes_existing_draft_record(
        self,
        app,
        user_id: str,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        """Organizer can publish an existing draft record."""
        viewer_id = await _new_user(session_factory)
        counterpart_id = await _new_user(session_factory)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            # First create a record
            create_response = await client.post(
                "/records/post-hoc",
                headers=auth_headers(user_id),
                json={
                    "counterpart_id": counterpart_id,
                    "conducted_at": "2026-03-20T14:00:00+09:00",
                },
            )
            record_id = create_response.json()["record_id"]

            # Then publish
            response = await client.post(
                f"/records/{record_id}/publish",
                headers=auth_headers(user_id),
                json={"viewer_ids": [viewer_id]},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["record_id"] == record_id

    async def test_re_publish_returns_409(
        self,
        app,
        user_id: str,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        """Re-publishing an already published record returns 409."""
        counterpart_id = await _new_user(session_factory)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            # Create
            create_response = await client.post(
                "/records/post-hoc",
                headers=auth_headers(user_id),
                json={
                    "counterpart_id": counterpart_id,
                    "conducted_at": "2026-03-20T14:00:00+09:00",
                },
            )
            record_id = create_response.json()["record_id"]

            # Publish first time
            await client.post(
                f"/records/{record_id}/publish",
                headers=auth_headers(user_id),
                json={"viewer_ids": []},
            )

            # Publish again
            response = await client.post(
                f"/records/{record_id}/publish",
                headers=auth_headers(user_id),
                json={"viewer_ids": []},
            )

        assert response.status_code == 409


# -----------------------------------------------------------------------
# POST /records/{id}/viewed
# -----------------------------------------------------------------------


class TestMarkRecordAsViewedAuth:
    """POST /records/{id}/viewed -- authentication checks."""

    async def test_returns_401_without_auth_header(self, app) -> None:
        """Request without Authorization header returns 401."""
        record_id = str(uuid.uuid4())
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            response = await client.post(
                f"/records/{record_id}/viewed",
            )

        assert response.status_code == 401


class TestMarkRecordAsViewedIntegration:
    """POST /records/{id}/viewed -- authenticated access."""

    async def test_returns_404_for_nonexistent_record(self, app, user_id: str) -> None:
        """Marking a nonexistent record as viewed returns 404."""
        record_id = str(uuid.uuid4())
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            response = await client.post(
                f"/records/{record_id}/viewed",
                headers=auth_headers(user_id),
            )

        assert response.status_code == 404

    async def test_organizer_marks_draft_as_viewed(
        self,
        app,
        user_id: str,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        """Organizer can mark their own draft record as viewed."""
        counterpart_id = await _new_user(session_factory)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            # Create a record
            create_response = await client.post(
                "/records/post-hoc",
                headers=auth_headers(user_id),
                json={
                    "counterpart_id": counterpart_id,
                    "conducted_at": "2026-03-20T14:00:00+09:00",
                },
            )
            record_id = create_response.json()["record_id"]

            # Mark as viewed
            response = await client.post(
                f"/records/{record_id}/viewed",
                headers=auth_headers(user_id),
            )

        assert response.status_code == 200
        data = response.json()
        assert data["record_id"] == record_id

    async def test_returns_403_for_non_visible_user(
        self,
        app,
        user_id: str,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        """A user without visibility cannot mark the record as viewed."""
        stranger_id = await _new_user(session_factory)
        counterpart_id = await _new_user(session_factory)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            # Create a record as organizer
            create_response = await client.post(
                "/records/post-hoc",
                headers=auth_headers(user_id),
                json={
                    "counterpart_id": counterpart_id,
                    "conducted_at": "2026-03-20T14:00:00+09:00",
                },
            )
            record_id = create_response.json()["record_id"]

            # Stranger tries to mark as viewed
            response = await client.post(
                f"/records/{record_id}/viewed",
                headers=auth_headers(stranger_id),
            )

        assert response.status_code == 403

    async def test_marks_published_record_as_viewed_twice(
        self,
        app,
        user_id: str,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        """Marking a record as viewed twice succeeds (idempotent update)."""
        counterpart_id = await _new_user(session_factory)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            # Create and publish
            create_response = await client.post(
                "/records/post-hoc",
                headers=auth_headers(user_id),
                json={
                    "counterpart_id": counterpart_id,
                    "conducted_at": "2026-03-20T14:00:00+09:00",
                },
            )
            record_id = create_response.json()["record_id"]
            await client.post(
                f"/records/{record_id}/publish",
                headers=auth_headers(user_id),
                json={"viewer_ids": []},
            )

            # Mark as viewed twice
            response1 = await client.post(
                f"/records/{record_id}/viewed",
                headers=auth_headers(user_id),
            )
            response2 = await client.post(
                f"/records/{record_id}/viewed",
                headers=auth_headers(user_id),
            )

        assert response1.status_code == 200
        assert response2.status_code == 200


# -----------------------------------------------------------------------
# POST /records/from-schedule
# -----------------------------------------------------------------------


class TestCreateRecordFromScheduleAuth:
    """POST /records/from-schedule -- authentication checks."""

    async def test_returns_401_without_auth_header(self, app) -> None:
        """Request without Authorization header returns 401."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            response = await client.post(
                "/records/from-schedule",
                json={
                    "schedule_id": str(uuid.uuid4()),
                    "conducted_at": _future(0),
                },
            )

        assert response.status_code == 401


class TestCreateRecordFromSchedule:
    """POST /records/from-schedule -- record creation from schedule."""

    async def test_creates_record_and_returns_201(
        self,
        app,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        """Creating a record from a schedule returns 201 and persists the row."""
        organizer_id = await _new_user(session_factory)
        cp_id = await _new_user(session_factory)

        transport = ASGITransport(app=app)

        # First create a schedule via the preparation API
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            schedule_resp = await client.post(
                "/schedules",
                headers=auth_headers(organizer_id),
                json={
                    "counterpart_id": cp_id,
                    "scheduled_at": _future(30),
                    "title": "Record from schedule test",
                },
            )
        assert schedule_resp.status_code == 201
        schedule_id = schedule_resp.json()["schedule_id"]

        # Create record from schedule
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            response = await client.post(
                "/records/from-schedule",
                headers=auth_headers(organizer_id),
                json={
                    "schedule_id": schedule_id,
                    "conducted_at": _future(0),
                },
            )

        assert response.status_code == 201
        data = response.json()
        record_id = data["record_id"]
        uuid.UUID(record_id)  # validates UUID format

        # Verify DB: record row exists and is linked to the schedule
        async with session_factory() as s:
            from contexts.record.infrastructure.tables import RecordTable

            result = await s.execute(
                select(RecordTable).where(RecordTable.id == record_id)
            )
            row = result.scalar_one()
            assert row.schedule_id == schedule_id
            assert row.organizer_id == organizer_id
            assert row.counterpart_id == cp_id
            assert row.status == "draft"

    async def test_returns_404_for_nonexistent_schedule(
        self, app, user_id: str
    ) -> None:
        """Creating a record from a nonexistent schedule returns 404."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            response = await client.post(
                "/records/from-schedule",
                headers=auth_headers(user_id),
                json={
                    "schedule_id": str(uuid.uuid4()),
                    "conducted_at": _future(0),
                },
            )

        assert response.status_code == 404


# -----------------------------------------------------------------------
# PUT /records/{id}/memo
# -----------------------------------------------------------------------


class TestUpdateMemoAuth:
    """PUT /records/{id}/memo -- authentication checks."""

    async def test_returns_401_without_auth_header(self, app) -> None:
        """Request without Authorization header returns 401."""
        record_id = str(uuid.uuid4())
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            response = await client.put(
                f"/records/{record_id}/memo",
                json={"memo": "some text"},
            )

        assert response.status_code == 401


class TestUpdateMemo:
    """PUT /records/{id}/memo -- memo update."""

    async def test_updates_memo_and_returns_200(
        self,
        app,
        user_id: str,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        """Updating a memo returns 200 and persists the new memo in DB."""
        counterpart_id = await _new_user(session_factory)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            # Create a record first
            create_response = await client.post(
                "/records/post-hoc",
                headers=auth_headers(user_id),
                json={
                    "counterpart_id": counterpart_id,
                    "conducted_at": _future(0),
                },
            )
            record_id = create_response.json()["record_id"]

            # Update memo
            response = await client.put(
                f"/records/{record_id}/memo",
                headers=auth_headers(user_id),
                json={"memo": "Updated memo content"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["record_id"] == record_id

        # Verify DB: memo is updated
        async with session_factory() as s:
            from contexts.record.infrastructure.tables import RecordTable

            result = await s.execute(
                select(RecordTable).where(RecordTable.id == record_id)
            )
            row = result.scalar_one()
            assert row.memo == "Updated memo content"

    async def test_returns_404_for_nonexistent_record(self, app, user_id: str) -> None:
        """Updating a memo for a nonexistent record returns 404."""
        record_id = str(uuid.uuid4())
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            response = await client.put(
                f"/records/{record_id}/memo",
                headers=auth_headers(user_id),
                json={"memo": "some text"},
            )

        assert response.status_code == 404


# -----------------------------------------------------------------------
# POST /records/{id}/agendas/{agenda_id}/confirm
# -----------------------------------------------------------------------


class TestConfirmAgendaAuth:
    """POST /records/{id}/agendas/{agenda_id}/confirm -- authentication checks."""

    async def test_returns_401_without_auth_header(self, app) -> None:
        """Request without Authorization header returns 401."""
        record_id = str(uuid.uuid4())
        agenda_id = str(uuid.uuid4())
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            response = await client.post(
                f"/records/{record_id}/agendas/{agenda_id}/confirm",
            )

        assert response.status_code == 401


class TestConfirmAgenda:
    """POST /records/{id}/agendas/{agenda_id}/confirm -- agenda confirmation."""

    async def test_confirms_agenda_and_returns_200(
        self,
        app,
        user_id: str,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        """Confirming an agenda returns 200 and persists the confirmed state in DB."""
        counterpart_id = await _new_user(session_factory)
        agenda_id = str(uuid.uuid4())

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            # Create a record first
            create_response = await client.post(
                "/records/post-hoc",
                headers=auth_headers(user_id),
                json={
                    "counterpart_id": counterpart_id,
                    "conducted_at": _future(0),
                },
            )
            record_id = create_response.json()["record_id"]

            # Confirm agenda
            response = await client.post(
                f"/records/{record_id}/agendas/{agenda_id}/confirm",
                headers=auth_headers(user_id),
            )

        assert response.status_code == 200
        data = response.json()
        assert data["record_id"] == record_id
        assert data["agenda_id"] == agenda_id

        # Verify DB: confirmed agenda row exists
        async with session_factory() as s:
            from contexts.record.infrastructure.tables import (
                RecordConfirmedAgendaTable,
            )

            result = await s.execute(
                select(RecordConfirmedAgendaTable).where(
                    RecordConfirmedAgendaTable.record_id == record_id,
                    RecordConfirmedAgendaTable.agenda_id == agenda_id,
                )
            )
            row = result.scalar_one()
            assert row.record_id == record_id
            assert row.agenda_id == agenda_id

    async def test_returns_404_for_nonexistent_record(self, app, user_id: str) -> None:
        """Confirming an agenda for a nonexistent record returns 404."""
        record_id = str(uuid.uuid4())
        agenda_id = str(uuid.uuid4())
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            response = await client.post(
                f"/records/{record_id}/agendas/{agenda_id}/confirm",
                headers=auth_headers(user_id),
            )

        assert response.status_code == 404
