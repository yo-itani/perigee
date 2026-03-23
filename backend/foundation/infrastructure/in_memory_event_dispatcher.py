from __future__ import annotations

from collections import defaultdict
from collections.abc import Awaitable, Callable
from typing import Any

from foundation.domain.event_dispatcher import EventDispatcher
from shared.domain.events import DomainEvent

EventHandler = Callable[[DomainEvent], Awaitable[None]]


class InMemoryEventDispatcher(EventDispatcher):
    """In-memory event dispatcher that routes events to registered handlers.

    Handlers are registered per event type.  When ``dispatch`` is called,
    each event is delivered to all handlers registered for its concrete
    type.

    Example::

        dispatcher = InMemoryEventDispatcher()
        dispatcher.register(RecordPublished, notify_slack)

        # After UoW commit
        events = entity.collect_events()
        await dispatcher.dispatch(events)
    """

    def __init__(self) -> None:
        self._handlers: dict[type[DomainEvent], list[EventHandler]] = defaultdict(list)

    def register(
        self,
        event_type: type[DomainEvent],
        handler: EventHandler,
    ) -> None:
        """Register a handler for the given event type."""
        self._handlers[event_type].append(handler)

    async def dispatch(self, events: list[DomainEvent]) -> None:
        """Dispatch each event to all registered handlers for its type."""
        for event in events:
            handlers = self._handlers.get(type(event), [])
            for handler in handlers:
                await handler(event)

    @property
    def handlers(self) -> dict[type[Any], tuple[EventHandler, ...]]:
        """Expose registered handlers as an immutable view (useful for testing).

        Values are tuples so that callers cannot mutate the internal
        handler lists.
        """
        return {k: tuple(v) for k, v in self._handlers.items()}
