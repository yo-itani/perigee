from __future__ import annotations

from abc import ABC, abstractmethod

from shared.domain.events import DomainEvent


class EventDispatcher(ABC):
    """Abstract base class for domain event dispatchers.

    Implementations are responsible for delivering domain events to
    registered handlers.
    """

    @abstractmethod
    async def dispatch(self, events: list[DomainEvent]) -> None:
        """Dispatch the given events to all registered handlers."""
