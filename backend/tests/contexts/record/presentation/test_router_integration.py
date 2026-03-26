"""Integration tests for Record context API endpoints.

These tests exercise the full HTTP layer (router -> DI -> use case -> repository -> DB)
using the real FastAPI app with httpx.AsyncClient.  No DI overrides are used.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from api.event_setup import create_event_dispatcher
from api.exception_handlers import register_exception_handlers
from api.register_routers import register_routers

pytestmark = pytest.mark.integration

_BASE_URL = "http://test"


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
def user_id() -> str:
    return str(uuid.uuid4())


class TestCreatePostHocRecordAuth:
    """POST /records/post-hoc -- authentication checks."""

    async def test_returns_401_without_auth_header(self, app) -> None:
        """Request without X-User-Id header returns 401."""
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

    async def test_creates_record_and_returns_201(self, app, user_id: str) -> None:
        """An authenticated user can create a post-hoc record."""
        counterpart_id = str(uuid.uuid4())
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            response = await client.post(
                "/records/post-hoc",
                headers={"X-User-Id": user_id},
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
        """Request without X-User-Id header returns 401."""
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
                headers={"X-User-Id": user_id},
            )

        assert response.status_code == 404

    async def test_returns_suggestions_for_existing_record(
        self, app, user_id: str
    ) -> None:
        """Organizer can get suggested viewers for an existing record."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            # First create a record
            create_response = await client.post(
                "/records/post-hoc",
                headers={"X-User-Id": user_id},
                json={
                    "counterpart_id": str(uuid.uuid4()),
                    "conducted_at": "2026-03-20T14:00:00+09:00",
                },
            )
            record_id = create_response.json()["record_id"]

            # Then get suggested viewers
            response = await client.get(
                f"/records/{record_id}/suggested-viewers",
                headers={"X-User-Id": user_id},
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
        """Request without X-User-Id header returns 401."""
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
                headers={"X-User-Id": user_id},
                json={"viewer_ids": [str(uuid.uuid4())]},
            )

        assert response.status_code == 404

    async def test_sets_viewers_for_existing_record(self, app, user_id: str) -> None:
        """Organizer can set viewers for an existing record."""
        viewer_id = str(uuid.uuid4())
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            # First create a record
            create_response = await client.post(
                "/records/post-hoc",
                headers={"X-User-Id": user_id},
                json={
                    "counterpart_id": str(uuid.uuid4()),
                    "conducted_at": "2026-03-20T14:00:00+09:00",
                },
            )
            record_id = create_response.json()["record_id"]

            # Then set viewers
            response = await client.put(
                f"/records/{record_id}/viewers",
                headers={"X-User-Id": user_id},
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
        """Request without X-User-Id header returns 401."""
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
                headers={"X-User-Id": user_id},
                json={"viewer_ids": []},
            )

        assert response.status_code == 404

    async def test_publishes_existing_draft_record(self, app, user_id: str) -> None:
        """Organizer can publish an existing draft record."""
        viewer_id = str(uuid.uuid4())
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            # First create a record
            create_response = await client.post(
                "/records/post-hoc",
                headers={"X-User-Id": user_id},
                json={
                    "counterpart_id": str(uuid.uuid4()),
                    "conducted_at": "2026-03-20T14:00:00+09:00",
                },
            )
            record_id = create_response.json()["record_id"]

            # Then publish
            response = await client.post(
                f"/records/{record_id}/publish",
                headers={"X-User-Id": user_id},
                json={"viewer_ids": [viewer_id]},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["record_id"] == record_id

    async def test_re_publish_returns_409(self, app, user_id: str) -> None:
        """Re-publishing an already published record returns 409."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            # Create
            create_response = await client.post(
                "/records/post-hoc",
                headers={"X-User-Id": user_id},
                json={
                    "counterpart_id": str(uuid.uuid4()),
                    "conducted_at": "2026-03-20T14:00:00+09:00",
                },
            )
            record_id = create_response.json()["record_id"]

            # Publish first time
            await client.post(
                f"/records/{record_id}/publish",
                headers={"X-User-Id": user_id},
                json={"viewer_ids": []},
            )

            # Publish again
            response = await client.post(
                f"/records/{record_id}/publish",
                headers={"X-User-Id": user_id},
                json={"viewer_ids": []},
            )

        assert response.status_code == 409


# -----------------------------------------------------------------------
# POST /records/{id}/viewed
# -----------------------------------------------------------------------


class TestMarkRecordAsViewedAuth:
    """POST /records/{id}/viewed -- authentication checks."""

    async def test_returns_401_without_auth_header(self, app) -> None:
        """Request without X-User-Id header returns 401."""
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
                headers={"X-User-Id": user_id},
            )

        assert response.status_code == 404

    async def test_organizer_marks_draft_as_viewed(self, app, user_id: str) -> None:
        """Organizer can mark their own draft record as viewed."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            # Create a record
            create_response = await client.post(
                "/records/post-hoc",
                headers={"X-User-Id": user_id},
                json={
                    "counterpart_id": str(uuid.uuid4()),
                    "conducted_at": "2026-03-20T14:00:00+09:00",
                },
            )
            record_id = create_response.json()["record_id"]

            # Mark as viewed
            response = await client.post(
                f"/records/{record_id}/viewed",
                headers={"X-User-Id": user_id},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["record_id"] == record_id

    async def test_returns_403_for_non_visible_user(self, app, user_id: str) -> None:
        """A user without visibility cannot mark the record as viewed."""
        stranger_id = str(uuid.uuid4())
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            # Create a record as organizer
            create_response = await client.post(
                "/records/post-hoc",
                headers={"X-User-Id": user_id},
                json={
                    "counterpart_id": str(uuid.uuid4()),
                    "conducted_at": "2026-03-20T14:00:00+09:00",
                },
            )
            record_id = create_response.json()["record_id"]

            # Stranger tries to mark as viewed
            response = await client.post(
                f"/records/{record_id}/viewed",
                headers={"X-User-Id": stranger_id},
            )

        assert response.status_code == 403

    async def test_marks_published_record_as_viewed_twice(
        self, app, user_id: str
    ) -> None:
        """Marking a record as viewed twice succeeds (idempotent update)."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            # Create and publish
            create_response = await client.post(
                "/records/post-hoc",
                headers={"X-User-Id": user_id},
                json={
                    "counterpart_id": str(uuid.uuid4()),
                    "conducted_at": "2026-03-20T14:00:00+09:00",
                },
            )
            record_id = create_response.json()["record_id"]
            await client.post(
                f"/records/{record_id}/publish",
                headers={"X-User-Id": user_id},
                json={"viewer_ids": []},
            )

            # Mark as viewed twice
            response1 = await client.post(
                f"/records/{record_id}/viewed",
                headers={"X-User-Id": user_id},
            )
            response2 = await client.post(
                f"/records/{record_id}/viewed",
                headers={"X-User-Id": user_id},
            )

        assert response1.status_code == 200
        assert response2.status_code == 200
