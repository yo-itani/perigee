from dataclasses import dataclass
from datetime import datetime

import pytest

from foundation.infrastructure.in_memory_event_dispatcher import InMemoryEventDispatcher
from shared.domain.events import DomainEvent


@dataclass(frozen=True)
class _SampleEvent(DomainEvent):
    value: str


@dataclass(frozen=True)
class _OtherEvent(DomainEvent):
    value: int


class TestInMemoryEventDispatcher:
    @pytest.fixture
    def dispatcher(self) -> InMemoryEventDispatcher:
        return InMemoryEventDispatcher()

    async def test_dispatch_calls_registered_handler(
        self, dispatcher: InMemoryEventDispatcher
    ) -> None:
        received: list[DomainEvent] = []

        async def handler(event: DomainEvent) -> None:
            received.append(event)

        dispatcher.register(_SampleEvent, handler)
        event = _SampleEvent(occurred_at=datetime(2026, 1, 1), value="hello")
        await dispatcher.dispatch([event])

        assert len(received) == 1
        assert received[0] is event

    async def test_dispatch_multiple_handlers(
        self, dispatcher: InMemoryEventDispatcher
    ) -> None:
        calls_a: list[DomainEvent] = []
        calls_b: list[DomainEvent] = []

        async def handler_a(event: DomainEvent) -> None:
            calls_a.append(event)

        async def handler_b(event: DomainEvent) -> None:
            calls_b.append(event)

        dispatcher.register(_SampleEvent, handler_a)
        dispatcher.register(_SampleEvent, handler_b)

        event = _SampleEvent(occurred_at=datetime(2026, 1, 1), value="test")
        await dispatcher.dispatch([event])

        assert len(calls_a) == 1
        assert len(calls_b) == 1

    async def test_dispatch_routes_by_event_type(
        self, dispatcher: InMemoryEventDispatcher
    ) -> None:
        sample_calls: list[DomainEvent] = []
        other_calls: list[DomainEvent] = []

        async def sample_handler(event: DomainEvent) -> None:
            sample_calls.append(event)

        async def other_handler(event: DomainEvent) -> None:
            other_calls.append(event)

        dispatcher.register(_SampleEvent, sample_handler)
        dispatcher.register(_OtherEvent, other_handler)

        sample = _SampleEvent(occurred_at=datetime(2026, 1, 1), value="a")
        other = _OtherEvent(occurred_at=datetime(2026, 1, 1), value=42)
        await dispatcher.dispatch([sample, other])

        assert len(sample_calls) == 1
        assert len(other_calls) == 1

    async def test_dispatch_ignores_unregistered_event_types(
        self, dispatcher: InMemoryEventDispatcher
    ) -> None:
        event = _SampleEvent(occurred_at=datetime(2026, 1, 1), value="ignored")
        # Should not raise
        await dispatcher.dispatch([event])

    async def test_dispatch_empty_list(
        self, dispatcher: InMemoryEventDispatcher
    ) -> None:
        await dispatcher.dispatch([])

    def test_handlers_property(self, dispatcher: InMemoryEventDispatcher) -> None:
        async def handler(event: DomainEvent) -> None:
            pass

        dispatcher.register(_SampleEvent, handler)
        assert _SampleEvent in dispatcher.handlers
        assert len(dispatcher.handlers[_SampleEvent]) == 1
