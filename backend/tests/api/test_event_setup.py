"""Tests for EventDispatcher initialization."""

from __future__ import annotations

from api.event_setup import create_event_dispatcher
from foundation.domain.event_dispatcher import EventDispatcher
from foundation.infrastructure.in_memory_event_dispatcher import InMemoryEventDispatcher


class TestCreateEventDispatcher:
    """Tests for the create_event_dispatcher factory."""

    def test_returns_in_memory_event_dispatcher(self) -> None:
        """create_event_dispatcher returns an InMemoryEventDispatcher."""
        dispatcher = create_event_dispatcher()
        assert isinstance(dispatcher, InMemoryEventDispatcher)

    def test_satisfies_event_dispatcher_interface(self) -> None:
        """The returned dispatcher satisfies the EventDispatcher ABC."""
        dispatcher = create_event_dispatcher()
        assert isinstance(dispatcher, EventDispatcher)

    def test_returns_new_instance_each_call(self) -> None:
        """Each call creates a fresh dispatcher (app startup calls once)."""
        d1 = create_event_dispatcher()
        d2 = create_event_dispatcher()
        assert d1 is not d2
