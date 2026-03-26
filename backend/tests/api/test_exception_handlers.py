"""Unit tests for the centralized exception handler registration."""

import uuid

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from api.exception_handlers import EXCEPTION_STATUS_MAP, register_exception_handlers
from contexts.notification.domain.exceptions import (
    InvalidReminderMinutesError,
)
from contexts.notification.domain.exceptions import (
    UnauthorizedOperationError as NotificationUnauthorizedOperationError,
)
from contexts.preparation.application.cancel_schedule_use_case import (
    ScheduleNotFoundError,
)
from contexts.preparation.domain.exceptions import (
    InvalidScheduleOperationError,
    ScheduleAlreadyCancelledError,
    UnauthorizedScheduleOperationError,
)
from contexts.preparation.domain.value_objects import ScheduleId
from contexts.record.application.complete_action_item import (
    ActionItemNotFoundError,
)
from contexts.record.domain.exceptions import (
    ActionItemAlreadyCompletedError,
    AgendaAlreadyConfirmedError,
    RecordAlreadyPublishedError,
    RecordNotPublishedError,
)
from contexts.record.domain.exceptions import (
    UnauthorizedOperationError as RecordUnauthorizedOperationError,
)
from contexts.record.domain.value_objects import ActionItemId


def _build_app_with_raising_route(exc: Exception) -> FastAPI:
    """Create a minimal FastAPI app that raises the given exception."""
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/raise")
    async def _raise() -> None:
        raise exc

    return app


async def _get_response(exc: Exception) -> tuple[int, dict]:
    app = _build_app_with_raising_route(exc)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/raise")
    return response.status_code, response.json()


class TestExceptionStatusMap:
    """Verify EXCEPTION_STATUS_MAP covers all expected categories."""

    def test_map_is_not_empty(self) -> None:
        assert len(EXCEPTION_STATUS_MAP) > 0

    def test_all_values_are_valid_http_status_codes(self) -> None:
        for exc_cls, status_code in EXCEPTION_STATUS_MAP.items():
            assert 400 <= status_code < 600, (
                f"{exc_cls.__name__} mapped to invalid status {status_code}"
            )

    def test_all_keys_are_exception_subclasses(self) -> None:
        for exc_cls in EXCEPTION_STATUS_MAP:
            assert issubclass(exc_cls, Exception), (
                f"{exc_cls} is not an Exception subclass"
            )


class TestForbiddenExceptions:
    """403 Forbidden responses."""

    async def test_record_unauthorized_operation(self) -> None:
        status, body = await _get_response(
            RecordUnauthorizedOperationError("No permission")
        )
        assert status == 403
        assert body == {"detail": "No permission"}

    async def test_notification_unauthorized_operation(self) -> None:
        status, body = await _get_response(
            NotificationUnauthorizedOperationError("Not allowed")
        )
        assert status == 403
        assert body == {"detail": "Not allowed"}

    async def test_unauthorized_schedule_operation(self) -> None:
        status, body = await _get_response(
            UnauthorizedScheduleOperationError("Forbidden")
        )
        assert status == 403
        assert body == {"detail": "Forbidden"}


class TestNotFoundExceptions:
    """404 Not Found responses."""

    async def test_schedule_not_found(self) -> None:
        schedule_id = ScheduleId(uuid.uuid4())
        status, body = await _get_response(ScheduleNotFoundError(schedule_id))
        assert status == 404
        assert str(schedule_id.value) in body["detail"]

    async def test_action_item_not_found(self) -> None:
        action_item_id = ActionItemId(uuid.uuid4())
        status, body = await _get_response(ActionItemNotFoundError(action_item_id))
        assert status == 404
        assert str(action_item_id.value) in body["detail"]


class TestConflictExceptions:
    """409 Conflict responses."""

    async def test_schedule_already_cancelled(self) -> None:
        status, body = await _get_response(ScheduleAlreadyCancelledError())
        assert status == 409
        assert body == {"detail": "Schedule is already cancelled."}

    async def test_record_already_published(self) -> None:
        status, body = await _get_response(RecordAlreadyPublishedError())
        assert status == 409
        assert body == {"detail": "Record is already published."}

    async def test_action_item_already_completed(self) -> None:
        status, body = await _get_response(ActionItemAlreadyCompletedError())
        assert status == 409
        assert body == {"detail": "Action item is already completed."}

    async def test_agenda_already_confirmed(self) -> None:
        status, body = await _get_response(AgendaAlreadyConfirmedError())
        assert status == 409
        assert body == {"detail": "Agenda is already confirmed."}


class TestUnprocessableEntityExceptions:
    """422 Unprocessable Entity responses."""

    async def test_invalid_reminder_minutes(self) -> None:
        status, body = await _get_response(InvalidReminderMinutesError())
        assert status == 422
        assert "reminder_minutes_before" in body["detail"]

    async def test_invalid_schedule_operation(self) -> None:
        status, body = await _get_response(
            InvalidScheduleOperationError("Bad operation")
        )
        assert status == 422
        assert body == {"detail": "Bad operation"}

    async def test_record_not_published(self) -> None:
        status, body = await _get_response(RecordNotPublishedError())
        assert status == 422
        assert body == {"detail": "Record is not published."}


class TestUnmappedException:
    """Unmapped exceptions are not caught by the handler.

    FastAPI's default ServerErrorMiddleware re-raises unmapped exceptions
    when ``debug=True`` (the default).  We verify that the exception is
    **not** intercepted by our handler, confirming that only registered
    exception classes are mapped.
    """

    async def test_unmapped_exception_is_not_handled(self) -> None:
        app = _build_app_with_raising_route(RuntimeError("unexpected"))
        transport = ASGITransport(app=app, raise_app_exceptions=False)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/raise")
        assert response.status_code == 500


class TestResponseFormat:
    """Verify the response body format is consistent."""

    async def test_detail_field_matches_exception_message(self) -> None:
        custom_msg = "Custom error message for testing"
        status, body = await _get_response(RecordAlreadyPublishedError(custom_msg))
        assert status == 409
        assert body == {"detail": custom_msg}

    async def test_default_message_used_when_no_custom_message(self) -> None:
        status, body = await _get_response(AgendaAlreadyConfirmedError())
        assert status == 409
        assert body == {"detail": "Agenda is already confirmed."}
