from __future__ import annotations

from abc import ABC, abstractmethod


class BaseRepository[TEntity, TId](ABC):
    """Abstract base class for all repositories.

    Type parameters:
        TEntity: The aggregate root entity type.
        TId: The entity's identifier type (typically a value object).

    Subclasses must implement ``get_by_id`` and ``save``.
    ``delete`` is intentionally excluded from the base interface;
    add it only in context-specific repository interfaces where needed.
    """

    @abstractmethod
    async def get_by_id(self, entity_id: TId) -> TEntity | None:
        """Return the entity with the given id, or ``None`` if not found."""

    @abstractmethod
    async def save(self, entity: TEntity) -> None:
        """Persist the entity (insert or update).

        Implementations must determine whether the entity is new or
        existing and issue the appropriate SQL statement.
        """
