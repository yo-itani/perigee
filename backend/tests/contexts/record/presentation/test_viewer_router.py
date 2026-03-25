"""Integration tests for Record viewer/reader API endpoints.

These tests exercise the full HTTP layer (router -> DI -> use case -> repository -> DB)
for the read-only record endpoints introduced in the record-viewer feature.

Endpoints covered:
- GET /records/{record_id}
- GET /records/{record_id}/comments
- GET /records/{record_id}/viewers
- GET /records/history
"""

from __future__ import annotations

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from api.event_setup import create_event_dispatcher
from api.exception_handlers import register_exception_handlers
from api.register_routers import register_routers
from contexts.record.application.publish_record import (
    PublishRecordInput,
    PublishRecordUseCase,
)
from contexts.record.domain.value_objects import RecordId
from contexts.record.infrastructure.sqlalchemy_record_repository import (
    SqlAlchemyRecordRepository,
)
from foundation.infrastructure.sqlalchemy_unit_of_work import SqlAlchemyUnitOfWork
from shared.domain.value_objects import UserId

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
def organizer_id() -> str:
    return str(uuid.uuid4())


@pytest.fixture
def counterpart_id() -> str:
    return str(uuid.uuid4())


@pytest.fixture
def unrelated_user_id() -> str:
    return str(uuid.uuid4())


async def _create_record(
    client: AsyncClient,
    organizer_id: str,
    counterpart_id: str,
) -> str:
    """Helper: create a post-hoc record and return its record_id."""
    response = await client.post(
        "/records/post-hoc",
        headers={"X-User-Id": organizer_id},
        json={
            "counterpart_id": counterpart_id,
            "conducted_at": "2026-03-20T14:00:00+09:00",
        },
    )
    assert response.status_code == 201
    return response.json()["record_id"]


async def _publish_record_via_use_case(
    record_id: str,
    organizer_id: str,
) -> None:
    """Helper: publish a record using the application use case directly.

    Since no publish HTTP endpoint is registered yet, this bypasses the
    HTTP layer and calls the use-case with a fresh DB session.
    """
    from foundation.db.session import async_session_factory

    async with async_session_factory() as session:
        repo = SqlAlchemyRecordRepository(session)
        uow = SqlAlchemyUnitOfWork(session)
        dispatcher = create_event_dispatcher()
        use_case = PublishRecordUseCase(
            record_repository=repo,
            unit_of_work=uow,
            event_dispatcher=dispatcher,
        )
        await use_case.execute(
            PublishRecordInput(
                record_id=RecordId(value=uuid.UUID(record_id)),
                actor_id=UserId(value=uuid.UUID(organizer_id)),
                viewer_ids=[],
            )
        )


# -----------------------------------------------------------------------
# GET /records/{record_id}
# -----------------------------------------------------------------------


class TestGetRecordDetail:
    """Tests for GET /records/{record_id}."""

    async def test_returns_401_without_auth_header(self, app) -> None:
        """Request without X-User-Id header returns 401."""
        record_id = str(uuid.uuid4())
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            response = await client.get(f"/records/{record_id}")

        assert response.status_code == 401

    async def test_returns_404_for_nonexistent_record(
        self, app, organizer_id: str
    ) -> None:
        """Requesting a non-existent record returns 404."""
        fake_id = str(uuid.uuid4())
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            response = await client.get(
                f"/records/{fake_id}",
                headers={"X-User-Id": organizer_id},
            )

        assert response.status_code == 404

    async def test_organizer_can_view_draft_record(
        self, app, organizer_id: str, counterpart_id: str
    ) -> None:
        """The organizer can view their own draft record."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            record_id = await _create_record(client, organizer_id, counterpart_id)
            response = await client.get(
                f"/records/{record_id}",
                headers={"X-User-Id": organizer_id},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["record_id"] == record_id
        assert data["organizer_id"] == organizer_id
        assert data["counterpart_id"] == counterpart_id
        assert data["status"] == "draft"
        assert data["memo"] == ""
        assert data["action_items"] == []
        assert data["confirmed_agenda_ids"] == []

    async def test_counterpart_cannot_view_draft_record(
        self, app, organizer_id: str, counterpart_id: str
    ) -> None:
        """The counterpart cannot view a draft record (only organizer can)."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            record_id = await _create_record(client, organizer_id, counterpart_id)
            response = await client.get(
                f"/records/{record_id}",
                headers={"X-User-Id": counterpart_id},
            )

        assert response.status_code == 403

    async def test_counterpart_can_view_published_record(
        self, app, organizer_id: str, counterpart_id: str
    ) -> None:
        """The counterpart can view a published record."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            record_id = await _create_record(client, organizer_id, counterpart_id)

        await _publish_record_via_use_case(record_id, organizer_id)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            response = await client.get(
                f"/records/{record_id}",
                headers={"X-User-Id": counterpart_id},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["record_id"] == record_id
        assert data["status"] == "published"

    async def test_unrelated_user_cannot_view_published_record(
        self, app, organizer_id: str, counterpart_id: str, unrelated_user_id: str
    ) -> None:
        """A user who is neither organizer, counterpart, nor viewer cannot view."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            record_id = await _create_record(client, organizer_id, counterpart_id)

        await _publish_record_via_use_case(record_id, organizer_id)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            response = await client.get(
                f"/records/{record_id}",
                headers={"X-User-Id": unrelated_user_id},
            )

        assert response.status_code == 403


# -----------------------------------------------------------------------
# GET /records/{record_id}/comments
# -----------------------------------------------------------------------


class TestListRecordComments:
    """Tests for GET /records/{record_id}/comments."""

    async def test_returns_401_without_auth_header(self, app) -> None:
        """Request without X-User-Id header returns 401."""
        record_id = str(uuid.uuid4())
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            response = await client.get(f"/records/{record_id}/comments")

        assert response.status_code == 401

    async def test_returns_404_for_nonexistent_record(
        self, app, organizer_id: str
    ) -> None:
        """Requesting comments for a non-existent record returns 404."""
        fake_id = str(uuid.uuid4())
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            response = await client.get(
                f"/records/{fake_id}/comments",
                headers={"X-User-Id": organizer_id},
            )

        assert response.status_code == 404

    async def test_returns_422_for_draft_record(
        self, app, organizer_id: str, counterpart_id: str
    ) -> None:
        """Listing comments on a draft record returns 422 (not published)."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            record_id = await _create_record(client, organizer_id, counterpart_id)
            response = await client.get(
                f"/records/{record_id}/comments",
                headers={"X-User-Id": organizer_id},
            )

        assert response.status_code == 422

    async def test_returns_empty_comments_for_published_record(
        self, app, organizer_id: str, counterpart_id: str
    ) -> None:
        """A freshly published record has no comments."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            record_id = await _create_record(client, organizer_id, counterpart_id)

        await _publish_record_via_use_case(record_id, organizer_id)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            response = await client.get(
                f"/records/{record_id}/comments",
                headers={"X-User-Id": organizer_id},
            )

        assert response.status_code == 200
        assert response.json()["comments"] == []

    async def test_counterpart_can_list_comments(
        self, app, organizer_id: str, counterpart_id: str
    ) -> None:
        """The counterpart can list comments on a published record."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            record_id = await _create_record(client, organizer_id, counterpart_id)

        await _publish_record_via_use_case(record_id, organizer_id)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            response = await client.get(
                f"/records/{record_id}/comments",
                headers={"X-User-Id": counterpart_id},
            )

        assert response.status_code == 200

    async def test_unrelated_user_cannot_list_comments(
        self, app, organizer_id: str, counterpart_id: str, unrelated_user_id: str
    ) -> None:
        """An unrelated user cannot list comments on a published record."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            record_id = await _create_record(client, organizer_id, counterpart_id)

        await _publish_record_via_use_case(record_id, organizer_id)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            response = await client.get(
                f"/records/{record_id}/comments",
                headers={"X-User-Id": unrelated_user_id},
            )

        assert response.status_code == 403


# -----------------------------------------------------------------------
# GET /records/{record_id}/viewers
# -----------------------------------------------------------------------


class TestGetViewers:
    """Tests for GET /records/{record_id}/viewers."""

    async def test_returns_401_without_auth_header(self, app) -> None:
        """Request without X-User-Id header returns 401."""
        record_id = str(uuid.uuid4())
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            response = await client.get(f"/records/{record_id}/viewers")

        assert response.status_code == 401

    async def test_returns_404_for_nonexistent_record(
        self, app, organizer_id: str
    ) -> None:
        """Requesting viewers for a non-existent record returns 404."""
        fake_id = str(uuid.uuid4())
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            response = await client.get(
                f"/records/{fake_id}/viewers",
                headers={"X-User-Id": organizer_id},
            )

        assert response.status_code == 404

    async def test_organizer_can_view_viewers(
        self, app, organizer_id: str, counterpart_id: str
    ) -> None:
        """The organizer can view the viewers list."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            record_id = await _create_record(client, organizer_id, counterpart_id)
            response = await client.get(
                f"/records/{record_id}/viewers",
                headers={"X-User-Id": organizer_id},
            )

        assert response.status_code == 200
        assert response.json()["viewer_ids"] == []

    async def test_counterpart_can_view_viewers_on_published(
        self, app, organizer_id: str, counterpart_id: str
    ) -> None:
        """The counterpart can view viewers on a published record."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            record_id = await _create_record(client, organizer_id, counterpart_id)

        await _publish_record_via_use_case(record_id, organizer_id)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            response = await client.get(
                f"/records/{record_id}/viewers",
                headers={"X-User-Id": counterpart_id},
            )

        assert response.status_code == 200

    async def test_counterpart_cannot_view_viewers_on_draft(
        self, app, organizer_id: str, counterpart_id: str
    ) -> None:
        """The counterpart cannot view viewers on a draft record."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            record_id = await _create_record(client, organizer_id, counterpart_id)
            response = await client.get(
                f"/records/{record_id}/viewers",
                headers={"X-User-Id": counterpart_id},
            )

        assert response.status_code == 403

    async def test_unrelated_user_cannot_view_viewers(
        self, app, organizer_id: str, counterpart_id: str, unrelated_user_id: str
    ) -> None:
        """An unrelated user cannot view the viewers list."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            record_id = await _create_record(client, organizer_id, counterpart_id)
            response = await client.get(
                f"/records/{record_id}/viewers",
                headers={"X-User-Id": unrelated_user_id},
            )

        assert response.status_code == 403


# -----------------------------------------------------------------------
# GET /records/history
# -----------------------------------------------------------------------


class TestListOneOnOneHistory:
    """Tests for GET /records/history."""

    async def test_returns_401_without_auth_header(
        self, app, organizer_id: str, counterpart_id: str
    ) -> None:
        """Request without X-User-Id header returns 401."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            response = await client.get(
                "/records/history",
                params={
                    "organizer_id": organizer_id,
                    "counterpart_id": counterpart_id,
                },
            )

        assert response.status_code == 401

    async def test_returns_empty_list_when_no_records(
        self, app, organizer_id: str, counterpart_id: str
    ) -> None:
        """Returns empty list when no published records exist for the pair."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            response = await client.get(
                "/records/history",
                headers={"X-User-Id": organizer_id},
                params={
                    "organizer_id": organizer_id,
                    "counterpart_id": counterpart_id,
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total_count"] == 0

    async def test_draft_records_not_included_in_history(
        self, app, organizer_id: str, counterpart_id: str
    ) -> None:
        """Draft records are not included in history (only published)."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            await _create_record(client, organizer_id, counterpart_id)
            response = await client.get(
                "/records/history",
                headers={"X-User-Id": organizer_id},
                params={
                    "organizer_id": organizer_id,
                    "counterpart_id": counterpart_id,
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total_count"] == 0

    async def test_published_records_included_in_history(
        self, app, organizer_id: str, counterpart_id: str
    ) -> None:
        """Published records appear in history."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            record_id = await _create_record(client, organizer_id, counterpart_id)

        await _publish_record_via_use_case(record_id, organizer_id)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            response = await client.get(
                "/records/history",
                headers={"X-User-Id": organizer_id},
                params={
                    "organizer_id": organizer_id,
                    "counterpart_id": counterpart_id,
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["record_id"] == record_id

    async def test_unrelated_user_sees_empty_history(
        self, app, organizer_id: str, counterpart_id: str, unrelated_user_id: str
    ) -> None:
        """An unrelated user does not see records in the history."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            record_id = await _create_record(client, organizer_id, counterpart_id)

        await _publish_record_via_use_case(record_id, organizer_id)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            response = await client.get(
                "/records/history",
                headers={"X-User-Id": unrelated_user_id},
                params={
                    "organizer_id": organizer_id,
                    "counterpart_id": counterpart_id,
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total_count"] == 0

    async def test_requires_organizer_id_and_counterpart_id(
        self, app, organizer_id: str
    ) -> None:
        """Missing required query parameters returns 422."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_BASE_URL) as client:
            response = await client.get(
                "/records/history",
                headers={"X-User-Id": organizer_id},
            )

        assert response.status_code == 422
