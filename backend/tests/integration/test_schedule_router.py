"""Integration tests for schedule state transitions and modifications.

Target endpoints:
- POST /schedules/consultation-request
- POST /schedules/{schedule_id}/confirm
- POST /schedules/{schedule_id}/reject
- POST /schedules/{schedule_id}/reschedule
- POST /schedules/{schedule_id}/cancel
- PUT  /schedules/{schedule_id}/title

These tests exercise the full HTTP layer (router -> DI -> use case -> repository -> DB)
using the real FastAPI app with httpx.AsyncClient.  No DI overrides are used.

Note on confirm / reject endpoints:
  These use AcceptConsultationRequestUseCase / RejectConsultationRequestUseCase
  which enforce ``actor == organizer``.  The intended flow is:
  1. Counterpart sends a consultation request (POST /schedules/consultation-request).
  2. Organizer confirms or rejects (POST /schedules/{id}/confirm or /reject).
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
from contexts.preparation.infrastructure.tables import ScheduleTable
from shared.domain.value_objects import UserId
from tests.helpers import auth_headers, create_test_user

pytestmark = pytest.mark.integration

_BASE_URL = "http://test"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


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


async def _create_consultation_request(
    app,
    organizer_id: str,
    counterpart_id: str,
    *,
    title: str = "Consultation meeting",
    days: int = 30,
) -> str:
    """Create a schedule via POST /schedules/consultation-request.

    The counterpart sends the request; the organizer can then confirm/reject.
    Returns the schedule_id.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
        resp = await client.post(
            "/schedules/consultation-request",
            headers=auth_headers(counterpart_id),
            json={
                "organizer_id": organizer_id,
                "scheduled_at": _future(days),
                "title": title,
                "agenda_topics": ["Agenda item"],
            },
        )
    assert resp.status_code == 201
    return resp.json()["schedule_id"]


async def _create_schedule_via_api(
    app,
    organizer_id: str,
    counterpart_id: str,
    *,
    title: str = "Test 1on1",
    days: int = 30,
) -> str:
    """Create a schedule via POST /schedules and return the schedule_id."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
        resp = await client.post(
            "/schedules",
            headers=auth_headers(organizer_id),
            json={
                "counterpart_id": counterpart_id,
                "scheduled_at": _future(days),
                "title": title,
            },
        )
    assert resp.status_code == 201
    return resp.json()["schedule_id"]


async def _get_schedule_status(
    session_factory: async_sessionmaker[AsyncSession],
    schedule_id: str,
) -> str:
    """Read the status column of a schedule from the DB."""
    async with session_factory() as s:
        result = await s.execute(
            select(ScheduleTable.status).where(ScheduleTable.id == schedule_id)
        )
        return result.scalar_one()


async def _get_schedule_row(
    session_factory: async_sessionmaker[AsyncSession],
    schedule_id: str,
) -> ScheduleTable:
    """Read the full schedule row from the DB."""
    async with session_factory() as s:
        result = await s.execute(
            select(ScheduleTable).where(ScheduleTable.id == schedule_id)
        )
        return result.scalar_one()


# =====================================================================
# POST /schedules/consultation-request
# =====================================================================


class TestSendConsultationRequest:
    """POST /schedules/consultation-request -- schedule creation via consultation."""

    async def test_creates_schedule_in_requested_status(
        self, app, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """Consultation request creates a schedule with status=requested."""
        organizer_id = await _new_user(session_factory)
        counterpart_id = await _new_user(session_factory)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            resp = await client.post(
                "/schedules/consultation-request",
                headers=auth_headers(counterpart_id),
                json={
                    "organizer_id": organizer_id,
                    "scheduled_at": _future(30),
                    "title": "Consultation meeting",
                    "agenda_topics": ["Topic A"],
                },
            )

        assert resp.status_code == 201
        schedule_id = resp.json()["schedule_id"]
        uuid.UUID(schedule_id)  # validates UUID format

        # Verify DB state
        status = await _get_schedule_status(session_factory, schedule_id)
        assert status == "requested"


# =====================================================================
# POST /schedules/{schedule_id}/confirm
# =====================================================================


class TestConfirmSchedule:
    """POST /schedules/{schedule_id}/confirm -- status transition to confirmed.

    The confirm endpoint uses AcceptConsultationRequestUseCase which
    requires actor == organizer.  Schedules must be created via
    consultation request (counterpart sends) so the organizer confirms.
    """

    async def test_confirm_requested_schedule(
        self, app, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """Organizer confirming a consultation request transitions to CONFIRMED."""
        organizer_id = await _new_user(session_factory)
        counterpart_id = await _new_user(session_factory)

        # Counterpart sends consultation request -> organizer confirms
        schedule_id = await _create_consultation_request(
            app, organizer_id, counterpart_id
        )
        assert await _get_schedule_status(session_factory, schedule_id) == "requested"

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            resp = await client.post(
                f"/schedules/{schedule_id}/confirm",
                headers=auth_headers(organizer_id),
            )

        assert resp.status_code == 204
        assert await _get_schedule_status(session_factory, schedule_id) == "confirmed"

    async def test_confirm_already_confirmed_returns_409(
        self, app, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """Confirming an already-confirmed schedule returns 409."""
        organizer_id = await _new_user(session_factory)
        counterpart_id = await _new_user(session_factory)

        schedule_id = await _create_consultation_request(
            app, organizer_id, counterpart_id
        )

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            # First confirm
            resp1 = await client.post(
                f"/schedules/{schedule_id}/confirm",
                headers=auth_headers(organizer_id),
            )
            assert resp1.status_code == 204

            # Second confirm -- no pending request
            resp2 = await client.post(
                f"/schedules/{schedule_id}/confirm",
                headers=auth_headers(organizer_id),
            )

        assert resp2.status_code == 409

    async def test_confirm_cancelled_schedule_returns_409(
        self, app, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """Confirming a CANCELLED schedule returns 409."""
        organizer_id = await _new_user(session_factory)
        counterpart_id = await _new_user(session_factory)

        schedule_id = await _create_consultation_request(
            app, organizer_id, counterpart_id
        )

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            # Cancel first (organizer can cancel)
            await client.post(
                f"/schedules/{schedule_id}/cancel",
                headers=auth_headers(organizer_id),
            )
            # Then try to confirm
            resp = await client.post(
                f"/schedules/{schedule_id}/confirm",
                headers=auth_headers(organizer_id),
            )

        assert resp.status_code == 409


# =====================================================================
# POST /schedules/{schedule_id}/reject
# =====================================================================


class TestRejectSchedule:
    """POST /schedules/{schedule_id}/reject -- status transition on rejection.

    The reject endpoint uses RejectConsultationRequestUseCase which
    requires actor == organizer.
    """

    async def test_reject_creation_request_cancels_schedule(
        self, app, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """Rejecting a CREATION request transitions schedule to CANCELLED."""
        organizer_id = await _new_user(session_factory)
        counterpart_id = await _new_user(session_factory)

        # Counterpart sends consultation request -> organizer rejects
        schedule_id = await _create_consultation_request(
            app, organizer_id, counterpart_id
        )

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            resp = await client.post(
                f"/schedules/{schedule_id}/reject",
                headers=auth_headers(organizer_id),
            )

        assert resp.status_code == 204
        assert await _get_schedule_status(session_factory, schedule_id) == "cancelled"

    async def test_reject_after_reschedule_returns_409_when_no_pending_request(
        self, app, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """Reject after reschedule returns 409 because no pending request exists.

        Flow:
        1. Counterpart sends consultation request -> REQUESTED
        2. Organizer confirms -> CONFIRMED
        3. Counterpart reschedules via /reschedule (change_scheduled_at) -> REQUESTED

        Since change_scheduled_at supersedes existing pending and does NOT create
        a new ConfirmationRequest, there is no pending request to reject.
        The reject endpoint returns NoPendingConfirmationRequestError (409).
        """
        organizer_id = await _new_user(session_factory)
        counterpart_id = await _new_user(session_factory)

        schedule_id = await _create_consultation_request(
            app, organizer_id, counterpart_id
        )

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            # Confirm first
            resp = await client.post(
                f"/schedules/{schedule_id}/confirm",
                headers=auth_headers(organizer_id),
            )
            assert resp.status_code == 204
            assert (
                await _get_schedule_status(session_factory, schedule_id) == "confirmed"
            )

            # Counterpart reschedules via /reschedule (uses change_scheduled_at)
            resp = await client.post(
                f"/schedules/{schedule_id}/reschedule",
                headers=auth_headers(counterpart_id),
                json={"new_scheduled_at": _future(60)},
            )
            assert resp.status_code == 204
            assert (
                await _get_schedule_status(session_factory, schedule_id) == "requested"
            )

            # Organizer tries to reject -- no pending request (change_scheduled_at
            # superseded the old one and did not create a new ConfirmationRequest)
            resp = await client.post(
                f"/schedules/{schedule_id}/reject",
                headers=auth_headers(organizer_id),
            )

        assert resp.status_code == 409

    async def test_reject_cancelled_schedule_returns_409(
        self, app, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """Rejecting a CANCELLED schedule returns 409."""
        organizer_id = await _new_user(session_factory)
        counterpart_id = await _new_user(session_factory)

        schedule_id = await _create_consultation_request(
            app, organizer_id, counterpart_id
        )

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            # Cancel first
            await client.post(
                f"/schedules/{schedule_id}/cancel",
                headers=auth_headers(organizer_id),
            )
            # Then try to reject
            resp = await client.post(
                f"/schedules/{schedule_id}/reject",
                headers=auth_headers(organizer_id),
            )

        assert resp.status_code == 409


# =====================================================================
# POST /schedules/{schedule_id}/reschedule
# =====================================================================


class TestRescheduleSchedule:
    """POST /schedules/{schedule_id}/reschedule -- datetime and status update.

    The reschedule endpoint uses RescheduleUseCase (change_scheduled_at)
    which allows any participant to reschedule.
    """

    async def test_reschedule_updates_status_to_requested(
        self, app, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """Rescheduling a confirmed schedule changes status to REQUESTED."""
        organizer_id = await _new_user(session_factory)
        counterpart_id = await _new_user(session_factory)

        schedule_id = await _create_consultation_request(
            app, organizer_id, counterpart_id, days=30
        )

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            # Confirm first
            resp = await client.post(
                f"/schedules/{schedule_id}/confirm",
                headers=auth_headers(organizer_id),
            )
            assert resp.status_code == 204
            assert (
                await _get_schedule_status(session_factory, schedule_id) == "confirmed"
            )

            new_scheduled_at = _future(60)
            resp = await client.post(
                f"/schedules/{schedule_id}/reschedule",
                headers=auth_headers(organizer_id),
                json={"new_scheduled_at": new_scheduled_at},
            )

        assert resp.status_code == 204
        assert await _get_schedule_status(session_factory, schedule_id) == "requested"

        row = await _get_schedule_row(session_factory, schedule_id)
        expected = datetime.fromisoformat(new_scheduled_at)
        assert row.scheduled_at.replace(tzinfo=UTC) == expected

    async def test_reschedule_from_requested_status(
        self, app, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """Rescheduling a REQUESTED schedule keeps status as REQUESTED."""
        organizer_id = await _new_user(session_factory)
        counterpart_id = await _new_user(session_factory)

        schedule_id = await _create_schedule_via_api(
            app, organizer_id, counterpart_id, days=30
        )
        assert await _get_schedule_status(session_factory, schedule_id) == "requested"

        new_scheduled_at = _future(45)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            resp = await client.post(
                f"/schedules/{schedule_id}/reschedule",
                headers=auth_headers(counterpart_id),
                json={"new_scheduled_at": new_scheduled_at},
            )

        assert resp.status_code == 204
        assert await _get_schedule_status(session_factory, schedule_id) == "requested"

        row = await _get_schedule_row(session_factory, schedule_id)
        expected = datetime.fromisoformat(new_scheduled_at)
        assert row.scheduled_at.replace(tzinfo=UTC) == expected

    async def test_reschedule_cancelled_schedule_returns_409(
        self, app, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """Rescheduling a CANCELLED schedule returns 409."""
        organizer_id = await _new_user(session_factory)
        counterpart_id = await _new_user(session_factory)

        schedule_id = await _create_schedule_via_api(app, organizer_id, counterpart_id)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            await client.post(
                f"/schedules/{schedule_id}/cancel",
                headers=auth_headers(organizer_id),
            )
            resp = await client.post(
                f"/schedules/{schedule_id}/reschedule",
                headers=auth_headers(organizer_id),
                json={"new_scheduled_at": _future(60)},
            )

        assert resp.status_code == 409

    async def test_reschedule_then_confirm_updates_scheduled_at(
        self, app, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """Rescheduling then confirming updates scheduled_at to the new time."""
        organizer_id = await _new_user(session_factory)
        counterpart_id = await _new_user(session_factory)

        schedule_id = await _create_consultation_request(
            app, organizer_id, counterpart_id, days=30
        )

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            # Counterpart reschedules (change_scheduled_at)
            new_scheduled_at = _future(60)
            resp = await client.post(
                f"/schedules/{schedule_id}/reschedule",
                headers=auth_headers(counterpart_id),
                json={"new_scheduled_at": new_scheduled_at},
            )
            assert resp.status_code == 204

            # Organizer confirms
            resp = await client.post(
                f"/schedules/{schedule_id}/confirm",
                headers=auth_headers(organizer_id),
            )
            assert resp.status_code == 204

        row_after = await _get_schedule_row(session_factory, schedule_id)
        assert row_after.status == "confirmed"
        expected = datetime.fromisoformat(new_scheduled_at)
        assert row_after.scheduled_at.replace(tzinfo=UTC) == expected


# =====================================================================
# POST /schedules/{schedule_id}/cancel
# =====================================================================


class TestCancelSchedule:
    """POST /schedules/{schedule_id}/cancel -- status transition to cancelled."""

    async def test_cancel_requested_schedule(
        self, app, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """Cancelling a REQUESTED schedule transitions it to CANCELLED."""
        organizer_id = await _new_user(session_factory)
        counterpart_id = await _new_user(session_factory)

        schedule_id = await _create_schedule_via_api(app, organizer_id, counterpart_id)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            resp = await client.post(
                f"/schedules/{schedule_id}/cancel",
                headers=auth_headers(organizer_id),
            )

        assert resp.status_code == 204
        assert await _get_schedule_status(session_factory, schedule_id) == "cancelled"

    async def test_cancel_confirmed_schedule(
        self, app, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """Cancelling a CONFIRMED schedule transitions it to CANCELLED."""
        organizer_id = await _new_user(session_factory)
        counterpart_id = await _new_user(session_factory)

        schedule_id = await _create_consultation_request(
            app, organizer_id, counterpart_id
        )

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            # Confirm first
            resp = await client.post(
                f"/schedules/{schedule_id}/confirm",
                headers=auth_headers(organizer_id),
            )
            assert resp.status_code == 204
            assert (
                await _get_schedule_status(session_factory, schedule_id) == "confirmed"
            )

            # Cancel
            resp = await client.post(
                f"/schedules/{schedule_id}/cancel",
                headers=auth_headers(organizer_id),
            )

        assert resp.status_code == 204
        assert await _get_schedule_status(session_factory, schedule_id) == "cancelled"

    async def test_cancel_already_cancelled_returns_409(
        self, app, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """Cancelling an already-cancelled schedule returns 409."""
        organizer_id = await _new_user(session_factory)
        counterpart_id = await _new_user(session_factory)

        schedule_id = await _create_schedule_via_api(app, organizer_id, counterpart_id)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            # First cancel
            resp1 = await client.post(
                f"/schedules/{schedule_id}/cancel",
                headers=auth_headers(organizer_id),
            )
            assert resp1.status_code == 204

            # Second cancel
            resp2 = await client.post(
                f"/schedules/{schedule_id}/cancel",
                headers=auth_headers(organizer_id),
            )

        assert resp2.status_code == 409


# =====================================================================
# Invalid state transitions (CANCELLED -> *)
# =====================================================================


class TestInvalidStateTransitionsFromCancelled:
    """Cancelled schedules reject all modification attempts."""

    async def test_cancelled_to_confirmed_rejected(
        self, app, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """CANCELLED -> CONFIRMED is rejected with 409."""
        organizer_id = await _new_user(session_factory)
        counterpart_id = await _new_user(session_factory)

        schedule_id = await _create_consultation_request(
            app, organizer_id, counterpart_id
        )

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            await client.post(
                f"/schedules/{schedule_id}/cancel",
                headers=auth_headers(organizer_id),
            )

            resp = await client.post(
                f"/schedules/{schedule_id}/confirm",
                headers=auth_headers(organizer_id),
            )

        assert resp.status_code == 409

    async def test_cancelled_to_reschedule_rejected(
        self, app, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """CANCELLED -> reschedule is rejected with 409."""
        organizer_id = await _new_user(session_factory)
        counterpart_id = await _new_user(session_factory)

        schedule_id = await _create_schedule_via_api(app, organizer_id, counterpart_id)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            await client.post(
                f"/schedules/{schedule_id}/cancel",
                headers=auth_headers(organizer_id),
            )

            resp = await client.post(
                f"/schedules/{schedule_id}/reschedule",
                headers=auth_headers(organizer_id),
                json={"new_scheduled_at": _future(60)},
            )

        assert resp.status_code == 409

    async def test_cancelled_to_reject_rejected(
        self, app, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """CANCELLED -> reject is rejected with 409."""
        organizer_id = await _new_user(session_factory)
        counterpart_id = await _new_user(session_factory)

        schedule_id = await _create_consultation_request(
            app, organizer_id, counterpart_id
        )

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            await client.post(
                f"/schedules/{schedule_id}/cancel",
                headers=auth_headers(organizer_id),
            )

            resp = await client.post(
                f"/schedules/{schedule_id}/reject",
                headers=auth_headers(organizer_id),
            )

        assert resp.status_code == 409


# =====================================================================
# PUT /schedules/{schedule_id}/title
# =====================================================================


class TestRenameSchedule:
    """PUT /schedules/{schedule_id}/title -- title update verification."""

    async def test_rename_schedule_updates_title_in_db(
        self, app, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """Renaming a schedule updates the title column in the DB."""
        organizer_id = await _new_user(session_factory)
        counterpart_id = await _new_user(session_factory)

        schedule_id = await _create_schedule_via_api(
            app, organizer_id, counterpart_id, title="Original Title"
        )

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            resp = await client.put(
                f"/schedules/{schedule_id}/title",
                headers=auth_headers(organizer_id),
                json={"title": "Updated Title"},
            )

        assert resp.status_code == 204

        row = await _get_schedule_row(session_factory, schedule_id)
        assert row.title == "Updated Title"

    async def test_rename_confirmed_schedule(
        self, app, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """Renaming a CONFIRMED schedule also works."""
        organizer_id = await _new_user(session_factory)
        counterpart_id = await _new_user(session_factory)

        schedule_id = await _create_consultation_request(
            app, organizer_id, counterpart_id, title="Before Confirm"
        )

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            await client.post(
                f"/schedules/{schedule_id}/confirm",
                headers=auth_headers(organizer_id),
            )

            resp = await client.put(
                f"/schedules/{schedule_id}/title",
                headers=auth_headers(organizer_id),
                json={"title": "After Confirm"},
            )

        assert resp.status_code == 204

        row = await _get_schedule_row(session_factory, schedule_id)
        assert row.title == "After Confirm"

    async def test_rename_cancelled_schedule(
        self, app, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """Renaming a CANCELLED schedule is allowed (group rename propagation)."""
        organizer_id = await _new_user(session_factory)
        counterpart_id = await _new_user(session_factory)

        schedule_id = await _create_schedule_via_api(
            app, organizer_id, counterpart_id, title="Pre-cancel"
        )

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            await client.post(
                f"/schedules/{schedule_id}/cancel",
                headers=auth_headers(organizer_id),
            )

            resp = await client.put(
                f"/schedules/{schedule_id}/title",
                headers=auth_headers(organizer_id),
                json={"title": "Post-cancel rename"},
            )

        assert resp.status_code == 204

        row = await _get_schedule_row(session_factory, schedule_id)
        assert row.title == "Post-cancel rename"
