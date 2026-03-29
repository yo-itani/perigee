"""Tests for application lifespan event dispatcher initialization."""

from __future__ import annotations

from api.event_setup import create_event_dispatcher
from foundation.infrastructure.in_memory_event_dispatcher import InMemoryEventDispatcher


class TestLifespanEventDispatcher:
    """Verify that create_event_dispatcher sets up an InMemoryEventDispatcher."""

    def test_create_event_dispatcher_returns_in_memory_instance(self) -> None:
        """create_event_dispatcher returns an InMemoryEventDispatcher with handlers."""
        dispatcher = create_event_dispatcher()
        assert isinstance(dispatcher, InMemoryEventDispatcher)
