"""Tests for shared DI providers."""

from __future__ import annotations

from unittest.mock import MagicMock

from api.dependencies import get_event_dispatcher, get_unit_of_work
from foundation.application.unit_of_work import UnitOfWork
from foundation.domain.event_dispatcher import EventDispatcher
from foundation.infrastructure.in_memory_event_dispatcher import InMemoryEventDispatcher
from foundation.infrastructure.sqlalchemy_unit_of_work import SqlAlchemyUnitOfWork


class TestGetUnitOfWork:
    """Tests for the get_unit_of_work provider."""

    def test_returns_sqlalchemy_unit_of_work(self) -> None:
        """get_unit_of_work returns a SqlAlchemyUnitOfWork instance."""
        uow = get_unit_of_work()
        assert isinstance(uow, SqlAlchemyUnitOfWork)

    def test_returns_unit_of_work_protocol(self) -> None:
        """The returned object satisfies the UnitOfWork abstract interface."""
        uow = get_unit_of_work()
        assert isinstance(uow, UnitOfWork)


class TestGetEventDispatcher:
    """Tests for the get_event_dispatcher provider."""

    def test_returns_dispatcher_from_app_state(self) -> None:
        """get_event_dispatcher reads from request.app.state.event_dispatcher."""
        dispatcher = InMemoryEventDispatcher()

        mock_request = MagicMock()
        mock_request.app.state.event_dispatcher = dispatcher

        result = get_event_dispatcher(mock_request)

        assert result is dispatcher
        assert isinstance(result, EventDispatcher)
