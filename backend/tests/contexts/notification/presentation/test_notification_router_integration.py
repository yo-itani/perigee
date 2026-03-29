"""Integration tests for notification (list / mark-as-read) API endpoints.

These tests exercise the full HTTP layer (router -> DI -> use case -> repository -> DB)
using the real FastAPI app with httpx.AsyncClient.  No DI overrides are used.

Target endpoints:
- GET  /notifications
- POST /notifications/{notification_id}/read
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from api.event_setup import create_event_dispatcher
from api.exception_handlers import register_exception_handlers
from api.register_routers import register_routers
from contexts.notification.infrastructure.tables import NotificationRecordTable
from shared.domain.value_objects import UserId
from tests.helpers import auth_headers, create_test_user

pytestmark = pytest.mark.integration

_BASE_URL = "http://test"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _new_user(session_factory: async_sessionmaker[AsyncSession]) -> str:
    """Create a new random user in the DB and return its id string."""
    uid = str(uuid.uuid4())
    async with session_factory() as s:
        await create_test_user(s, user_id=UserId(uuid.UUID(uid)))
        await s.commit()
    return uid


async def _insert_notification(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    recipient_id: str,
    notification_id: str | None = None,
    notification_type: str = "schedule_created",
    title: str = "Test notification",
    body: str = "Test body",
    link: str | None = None,
    is_read: bool = False,
    read_at: datetime | None = None,
) -> str:
    """Insert a notification_records row and return its id."""
    nid = notification_id or str(uuid.uuid4())
    now = datetime.now(UTC).replace(tzinfo=None)
    async with session_factory() as s:
        row = NotificationRecordTable(
            id=nid,
            recipient_id=recipient_id,
            notification_type=notification_type,
            title=title,
            body=body,
            link=link,
            is_read=is_read,
            read_at=read_at,
            created_at=now,
        )
        s.add(row)
        await s.commit()
    return nid


def _create_test_app():
    """Create a FastAPI app wired with routers and exception handlers."""
    from fastapi import FastAPI

    app = FastAPI()
    app.state.event_dispatcher = create_event_dispatcher()
    register_exception_handlers(app)
    register_routers(app)
    return app


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def app():
    return _create_test_app()


@pytest.fixture
async def user_id(session_factory: async_sessionmaker[AsyncSession]) -> str:
    return await _new_user(session_factory)


# ===========================================================================
# GET /notifications
# ===========================================================================


class TestListNotifications:
    """GET /notifications -- notification list retrieval."""

    async def test_returns_200_with_notifications(
        self,
        app,
        user_id: str,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        """Notifications inserted in DB are returned in the response."""
        nid = await _insert_notification(
            session_factory,
            recipient_id=user_id,
            title="Meeting scheduled",
            body="Your 1on1 has been scheduled.",
            link="/schedules/123",
        )

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            response = await client.get(
                "/notifications",
                headers=auth_headers(user_id),
            )

        assert response.status_code == 200
        data = response.json()
        notifications = data["notifications"]
        assert len(notifications) >= 1
        ids = [n["id"] for n in notifications]
        assert nid in ids
        # Verify the returned fields
        matching = [n for n in notifications if n["id"] == nid][0]
        assert matching["title"] == "Meeting scheduled"
        assert matching["body"] == "Your 1on1 has been scheduled."
        assert matching["link"] == "/schedules/123"
        assert matching["is_read"] is False
        assert matching["read_at"] is None

    async def test_returns_200_with_empty_list_when_no_notifications(
        self, app, user_id: str
    ) -> None:
        """A user with no notifications gets an empty list."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            response = await client.get(
                "/notifications",
                headers=auth_headers(user_id),
            )

        assert response.status_code == 200
        data = response.json()
        assert data["notifications"] == []

    async def test_does_not_include_other_users_notifications(
        self,
        app,
        user_id: str,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        """Notifications belonging to other users are not returned."""
        other_user_id = await _new_user(session_factory)

        # Insert notification for the other user
        other_nid = await _insert_notification(
            session_factory,
            recipient_id=other_user_id,
            title="Other user notification",
            body="Should not be visible",
        )

        # Insert notification for the current user
        my_nid = await _insert_notification(
            session_factory,
            recipient_id=user_id,
            title="My notification",
            body="Should be visible",
        )

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            response = await client.get(
                "/notifications",
                headers=auth_headers(user_id),
            )

        assert response.status_code == 200
        notifications = response.json()["notifications"]
        ids = [n["id"] for n in notifications]
        assert my_nid in ids
        assert other_nid not in ids

    async def test_unread_filter_returns_only_unread(
        self,
        app,
        user_id: str,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        """With unread=true, only unread notifications are returned."""
        now = datetime.now(UTC).replace(tzinfo=None)

        unread_nid = await _insert_notification(
            session_factory,
            recipient_id=user_id,
            title="Unread notification",
            body="Not read yet",
            is_read=False,
        )
        read_nid = await _insert_notification(
            session_factory,
            recipient_id=user_id,
            title="Read notification",
            body="Already read",
            is_read=True,
            read_at=now,
        )

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            response = await client.get(
                "/notifications",
                params={"unread": "true"},
                headers=auth_headers(user_id),
            )

        assert response.status_code == 200
        notifications = response.json()["notifications"]
        ids = [n["id"] for n in notifications]
        assert unread_nid in ids
        assert read_nid not in ids

    async def test_without_unread_filter_returns_all(
        self,
        app,
        user_id: str,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        """Without unread filter, both read and unread are returned."""
        now = datetime.now(UTC).replace(tzinfo=None)

        unread_nid = await _insert_notification(
            session_factory,
            recipient_id=user_id,
            title="Unread",
            body="body",
            is_read=False,
        )
        read_nid = await _insert_notification(
            session_factory,
            recipient_id=user_id,
            title="Read",
            body="body",
            is_read=True,
            read_at=now,
        )

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            response = await client.get(
                "/notifications",
                headers=auth_headers(user_id),
            )

        assert response.status_code == 200
        notifications = response.json()["notifications"]
        ids = [n["id"] for n in notifications]
        assert unread_nid in ids
        assert read_nid in ids

    async def test_returns_401_without_auth_header(self, app) -> None:
        """Request without Authorization header returns 401."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            response = await client.get("/notifications")

        assert response.status_code == 401


# ===========================================================================
# POST /notifications/{notification_id}/read
# ===========================================================================


class TestMarkNotificationAsRead:
    """POST /notifications/{notification_id}/read -- mark as read."""

    async def test_mark_as_read_returns_204_and_updates_db(
        self,
        app,
        user_id: str,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        """Marking an unread notification returns 204 and sets read_at in DB."""
        nid = await _insert_notification(
            session_factory,
            recipient_id=user_id,
            title="To be read",
            body="body",
        )

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            response = await client.post(
                f"/notifications/{nid}/read",
                headers=auth_headers(user_id),
            )

        assert response.status_code == 204

        # Verify DB: read_at is set via a separate session
        async with session_factory() as s:
            result = await s.execute(
                select(NotificationRecordTable).where(NotificationRecordTable.id == nid)
            )
            row = result.scalar_one()
            assert row.is_read is True
            assert row.read_at is not None

    async def test_nonexistent_notification_returns_404(
        self, app, user_id: str
    ) -> None:
        """Marking a non-existent notification returns 404."""
        fake_id = str(uuid.uuid4())

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            response = await client.post(
                f"/notifications/{fake_id}/read",
                headers=auth_headers(user_id),
            )

        assert response.status_code == 404

    async def test_other_users_notification_returns_403(
        self,
        app,
        user_id: str,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        """Marking another user's notification returns 403."""
        other_user_id = await _new_user(session_factory)
        nid = await _insert_notification(
            session_factory,
            recipient_id=other_user_id,
            title="Other user's notification",
            body="body",
        )

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            response = await client.post(
                f"/notifications/{nid}/read",
                headers=auth_headers(user_id),
            )

        assert response.status_code == 403

    async def test_already_read_notification_returns_204_idempotent(
        self,
        app,
        user_id: str,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        """Marking an already-read notification returns 204 (idempotent)."""
        now = datetime.now(UTC).replace(tzinfo=None)
        nid = await _insert_notification(
            session_factory,
            recipient_id=user_id,
            title="Already read",
            body="body",
            is_read=True,
            read_at=now,
        )

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            response = await client.post(
                f"/notifications/{nid}/read",
                headers=auth_headers(user_id),
            )

        assert response.status_code == 204

        # read_at should remain unchanged
        async with session_factory() as s:
            result = await s.execute(
                select(NotificationRecordTable).where(NotificationRecordTable.id == nid)
            )
            row = result.scalar_one()
            assert row.read_at == now

    async def test_mark_as_read_then_list_shows_read(
        self,
        app,
        user_id: str,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        """After marking as read, GET /notifications shows the notification as read."""
        nid = await _insert_notification(
            session_factory,
            recipient_id=user_id,
            title="Will be read",
            body="body",
        )

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            # Mark as read
            mark_resp = await client.post(
                f"/notifications/{nid}/read",
                headers=auth_headers(user_id),
            )
            assert mark_resp.status_code == 204

            # Verify via list endpoint
            list_resp = await client.get(
                "/notifications",
                headers=auth_headers(user_id),
            )

        assert list_resp.status_code == 200
        notifications = list_resp.json()["notifications"]
        matching = [n for n in notifications if n["id"] == nid]
        assert len(matching) == 1
        assert matching[0]["is_read"] is True
        assert matching[0]["read_at"] is not None

    async def test_mark_as_read_excluded_from_unread_filter(
        self,
        app,
        user_id: str,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        """After marking as read, the notification is excluded by unread filter."""
        nid = await _insert_notification(
            session_factory,
            recipient_id=user_id,
            title="To be read and filtered",
            body="body",
        )

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            # Mark as read
            await client.post(
                f"/notifications/{nid}/read",
                headers=auth_headers(user_id),
            )

            # List with unread filter
            response = await client.get(
                "/notifications",
                params={"unread": "true"},
                headers=auth_headers(user_id),
            )

        assert response.status_code == 200
        ids = [n["id"] for n in response.json()["notifications"]]
        assert nid not in ids

    async def test_returns_401_without_auth_header(self, app) -> None:
        """Request without Authorization header returns 401."""
        fake_id = str(uuid.uuid4())
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            response = await client.post(f"/notifications/{fake_id}/read")

        assert response.status_code == 401
