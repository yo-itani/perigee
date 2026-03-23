from dataclasses import FrozenInstanceError, dataclass
from datetime import datetime

import pytest

from shared.domain.events import DomainEvent


class TestDomainEvent:
    def test_is_frozen_dataclass(self) -> None:
        event = DomainEvent(occurred_at=datetime(2026, 1, 1))
        with pytest.raises(FrozenInstanceError):
            event.occurred_at = datetime(2026, 2, 1)  # type: ignore[misc]

    def test_occurred_at_field(self) -> None:
        ts = datetime(2026, 3, 15, 10, 30)
        event = DomainEvent(occurred_at=ts)
        assert event.occurred_at == ts

    def test_subclass_inherits_occurred_at(self) -> None:
        @dataclass(frozen=True)
        class ChildEvent(DomainEvent):
            detail: str

        ts = datetime(2026, 1, 1)
        child = ChildEvent(occurred_at=ts, detail="test")
        assert child.occurred_at == ts
        assert child.detail == "test"
        assert isinstance(child, DomainEvent)
