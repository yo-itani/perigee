from abc import ABC

from foundation.domain.event_dispatcher import EventDispatcher


class TestEventDispatcherInterface:
    def test_is_abstract(self) -> None:
        assert issubclass(EventDispatcher, ABC)

    def test_dispatch_is_abstract(self) -> None:
        assert "dispatch" in EventDispatcher.__abstractmethods__
