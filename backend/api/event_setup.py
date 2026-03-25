"""EventDispatcher initialization for the application lifecycle."""

from __future__ import annotations

from foundation.infrastructure.in_memory_event_dispatcher import InMemoryEventDispatcher


def create_event_dispatcher() -> InMemoryEventDispatcher:
    """Create an InMemoryEventDispatcher and register all event handlers.

    This function is called once at application startup.  The returned
    dispatcher is stored on ``app.state`` and shared across all requests.

    Returns:
        A fully-configured InMemoryEventDispatcher instance.
    """
    dispatcher = InMemoryEventDispatcher()

    # Register event handlers here as contexts are implemented.
    # Example:
    #   from contexts.notification.application.handlers import (
    #       schedule_created_handler,
    #   )
    #   from contexts.preparation.domain.events import ScheduleCreated
    #   dispatcher.register(ScheduleCreated, schedule_created_handler)

    return dispatcher
