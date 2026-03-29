"""Integration tests for action item and comment API endpoints.

These tests exercise the full HTTP layer (router -> DI -> use case -> repository -> DB)
using the real FastAPI app with httpx.AsyncClient.  No DI overrides are used.

Endpoints covered:
- POST /records/{record_id}/action-items (add action item)
- DELETE /records/{record_id}/action-items/{action_item_id} (delete action item)
- POST /action-items/{action_item_id}/complete (complete action item)
- POST /records/{record_id}/comments (add comment)
- GET /records/{record_id}/comments (list comments -- supplementary)
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
from contexts.record.infrastructure.tables import ActionItemTable, CommentTable
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
async def organizer_id(
    session_factory: async_sessionmaker[AsyncSession],
) -> str:
    return await _new_user(session_factory)


@pytest.fixture
async def counterpart_id(
    session_factory: async_sessionmaker[AsyncSession],
) -> str:
    return await _new_user(session_factory)


async def _create_record(
    client: AsyncClient,
    organizer_id: str,
    counterpart_id: str,
) -> str:
    """Helper: create a post-hoc record and return its record_id."""
    response = await client.post(
        "/records/post-hoc",
        headers=auth_headers(organizer_id),
        json={
            "counterpart_id": counterpart_id,
            "conducted_at": _future(0),
        },
    )
    assert response.status_code == 201
    return response.json()["record_id"]


async def _publish_record(
    client: AsyncClient,
    record_id: str,
    organizer_id: str,
) -> None:
    """Helper: publish a record via the HTTP endpoint."""
    response = await client.post(
        f"/records/{record_id}/publish",
        headers=auth_headers(organizer_id),
        json={"viewer_ids": []},
    )
    assert response.status_code == 200


# -----------------------------------------------------------------------
# POST /records/{record_id}/action-items
# -----------------------------------------------------------------------


class TestAddActionItemAuth:
    """POST /records/{record_id}/action-items -- authentication checks."""

    async def test_returns_401_without_auth_header(self, app) -> None:
        """Request without Authorization header returns 401."""
        record_id = str(uuid.uuid4())
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            response = await client.post(
                f"/records/{record_id}/action-items",
                json={"title": "Follow up"},
            )

        assert response.status_code == 401


class TestAddActionItem:
    """POST /records/{record_id}/action-items -- add action item."""

    async def test_adds_action_item_and_returns_201(
        self,
        app,
        organizer_id: str,
        counterpart_id: str,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        """Adding an action item returns 201 and persists the row in DB."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            record_id = await _create_record(client, organizer_id, counterpart_id)

            response = await client.post(
                f"/records/{record_id}/action-items",
                headers=auth_headers(organizer_id),
                json={"title": "Review design doc"},
            )

        assert response.status_code == 201
        data = response.json()
        action_item_id = data["action_item_id"]
        uuid.UUID(action_item_id)  # validates UUID format

        # Verify DB: action_items row exists
        async with session_factory() as s:
            result = await s.execute(
                select(ActionItemTable).where(ActionItemTable.id == action_item_id)
            )
            row = result.scalar_one()
            assert row.record_id == record_id
            assert row.title == "Review design doc"
            assert row.is_completed is False

    async def test_returns_404_for_nonexistent_record(
        self, app, organizer_id: str
    ) -> None:
        """Adding an action item to a nonexistent record returns 404."""
        record_id = str(uuid.uuid4())
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            response = await client.post(
                f"/records/{record_id}/action-items",
                headers=auth_headers(organizer_id),
                json={"title": "Follow up"},
            )

        assert response.status_code == 404


# -----------------------------------------------------------------------
# DELETE /records/{record_id}/action-items/{action_item_id}
# -----------------------------------------------------------------------


class TestDeleteActionItemAuth:
    """DELETE /records/{record_id}/action-items/{action_item_id} -- auth checks."""

    async def test_returns_401_without_auth_header(self, app) -> None:
        """Request without Authorization header returns 401."""
        record_id = str(uuid.uuid4())
        action_item_id = str(uuid.uuid4())
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            response = await client.delete(
                f"/records/{record_id}/action-items/{action_item_id}",
            )

        assert response.status_code == 401


class TestDeleteActionItem:
    """DELETE /records/{record_id}/action-items/{action_item_id} -- deletion."""

    async def test_deletes_action_item_from_db(
        self,
        app,
        organizer_id: str,
        counterpart_id: str,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        """Deleting an action item removes the row from the DB."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            record_id = await _create_record(client, organizer_id, counterpart_id)

            # Add an action item first
            add_response = await client.post(
                f"/records/{record_id}/action-items",
                headers=auth_headers(organizer_id),
                json={"title": "To be deleted"},
            )
            assert add_response.status_code == 201
            action_item_id = add_response.json()["action_item_id"]

            # Delete it
            response = await client.delete(
                f"/records/{record_id}/action-items/{action_item_id}",
                headers=auth_headers(organizer_id),
            )

        assert response.status_code == 200
        data = response.json()
        assert data["action_item_id"] == action_item_id

        # Verify DB: row no longer exists
        async with session_factory() as s:
            result = await s.execute(
                select(ActionItemTable).where(ActionItemTable.id == action_item_id)
            )
            row = result.scalar_one_or_none()
            assert row is None


# -----------------------------------------------------------------------
# POST /action-items/{action_item_id}/complete
# -----------------------------------------------------------------------


class TestCompleteActionItemAuth:
    """POST /action-items/{action_item_id}/complete -- authentication checks."""

    async def test_returns_401_without_auth_header(self, app) -> None:
        """Request without Authorization header returns 401."""
        action_item_id = str(uuid.uuid4())
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            response = await client.post(
                f"/action-items/{action_item_id}/complete",
            )

        assert response.status_code == 401


class TestCompleteActionItem:
    """POST /action-items/{action_item_id}/complete -- completion."""

    async def test_completes_action_item_and_sets_is_completed(
        self,
        app,
        organizer_id: str,
        counterpart_id: str,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        """Completing an action item sets is_completed to True in DB.

        Only the counterpart (not the organizer) is allowed to complete.
        """
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            record_id = await _create_record(client, organizer_id, counterpart_id)

            # Add an action item (organizer adds it)
            add_response = await client.post(
                f"/records/{record_id}/action-items",
                headers=auth_headers(organizer_id),
                json={"title": "Complete me"},
            )
            assert add_response.status_code == 201
            action_item_id = add_response.json()["action_item_id"]

            # Complete it (counterpart completes)
            response = await client.post(
                f"/action-items/{action_item_id}/complete",
                headers=auth_headers(counterpart_id),
            )

        assert response.status_code == 200
        data = response.json()
        assert data["action_item_id"] == action_item_id

        # Verify DB: is_completed is True
        async with session_factory() as s:
            result = await s.execute(
                select(ActionItemTable).where(ActionItemTable.id == action_item_id)
            )
            row = result.scalar_one()
            assert row.is_completed is True

    async def test_returns_404_for_nonexistent_action_item(
        self, app, organizer_id: str
    ) -> None:
        """Completing a nonexistent action item returns 404."""
        action_item_id = str(uuid.uuid4())
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            response = await client.post(
                f"/action-items/{action_item_id}/complete",
                headers=auth_headers(organizer_id),
            )

        assert response.status_code == 404


# -----------------------------------------------------------------------
# POST /records/{record_id}/comments
# -----------------------------------------------------------------------


class TestAddCommentAuth:
    """POST /records/{record_id}/comments -- authentication checks."""

    async def test_returns_401_without_auth_header(self, app) -> None:
        """Request without Authorization header returns 401."""
        record_id = str(uuid.uuid4())
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            response = await client.post(
                f"/records/{record_id}/comments",
                json={"body": "Nice session!"},
            )

        assert response.status_code == 401


class TestAddComment:
    """POST /records/{record_id}/comments -- add comment."""

    async def test_adds_comment_to_published_record_and_returns_201(
        self,
        app,
        organizer_id: str,
        counterpart_id: str,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        """Adding a comment to a published record returns 201 and persists the row."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            record_id = await _create_record(client, organizer_id, counterpart_id)
            await _publish_record(client, record_id, organizer_id)

            response = await client.post(
                f"/records/{record_id}/comments",
                headers=auth_headers(organizer_id),
                json={"body": "Great discussion today"},
            )

        assert response.status_code == 201
        data = response.json()
        comment_id = data["comment_id"]
        uuid.UUID(comment_id)  # validates UUID format

        # Verify DB: comments row exists
        async with session_factory() as s:
            result = await s.execute(
                select(CommentTable).where(CommentTable.id == comment_id)
            )
            row = result.scalar_one()
            assert row.record_id == record_id
            assert row.author_id == organizer_id
            assert row.body == "Great discussion today"

    async def test_returns_404_for_nonexistent_record(
        self, app, organizer_id: str
    ) -> None:
        """Adding a comment to a nonexistent record returns 404."""
        record_id = str(uuid.uuid4())
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            response = await client.post(
                f"/records/{record_id}/comments",
                headers=auth_headers(organizer_id),
                json={"body": "Hello"},
            )

        assert response.status_code == 404

    async def test_returns_422_for_draft_record(
        self,
        app,
        organizer_id: str,
        counterpart_id: str,
    ) -> None:
        """Adding a comment to a draft (unpublished) record returns 422."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            record_id = await _create_record(client, organizer_id, counterpart_id)

            response = await client.post(
                f"/records/{record_id}/comments",
                headers=auth_headers(organizer_id),
                json={"body": "Should fail"},
            )

        assert response.status_code == 422


# -----------------------------------------------------------------------
# GET /records/{record_id}/comments (supplementary)
# -----------------------------------------------------------------------


class TestListCommentsAfterAdd:
    """GET /records/{record_id}/comments -- verify added comments appear in list."""

    async def test_added_comment_appears_in_list(
        self,
        app,
        organizer_id: str,
        counterpart_id: str,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        """A comment added via POST appears in the GET comments list."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            record_id = await _create_record(client, organizer_id, counterpart_id)
            await _publish_record(client, record_id, organizer_id)

            # Add a comment
            add_response = await client.post(
                f"/records/{record_id}/comments",
                headers=auth_headers(organizer_id),
                json={"body": "Follow-up needed"},
            )
            assert add_response.status_code == 201
            comment_id = add_response.json()["comment_id"]

            # List comments
            list_response = await client.get(
                f"/records/{record_id}/comments",
                headers=auth_headers(organizer_id),
            )

        assert list_response.status_code == 200
        comments = list_response.json()["comments"]
        assert len(comments) >= 1
        comment_ids = [c["comment_id"] for c in comments]
        assert comment_id in comment_ids

        # Verify the comment content
        matching = [c for c in comments if c["comment_id"] == comment_id]
        assert matching[0]["body"] == "Follow-up needed"
        assert matching[0]["author_id"] == organizer_id
