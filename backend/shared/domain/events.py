from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class DomainEvent:
    """Base class for all domain events.

    All domain events must inherit from this class and include
    an ``occurred_at`` field that records when the event happened.
    """

    occurred_at: datetime
