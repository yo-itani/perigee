from __future__ import annotations


class OptimisticLockError(Exception):
    """Raised when an optimistic lock conflict is detected.

    This typically happens when ``save()`` attempts to update a row
    whose ``updated_at`` value no longer matches the one loaded by
    the aggregate, indicating that another transaction has modified
    the row since it was read.
    """

    def __init__(self, entity_type: str, entity_id: str) -> None:
        self.entity_type = entity_type
        self.entity_id = entity_id
        super().__init__(
            f"Optimistic lock conflict on {entity_type} (id={entity_id}): "
            "the entity was modified by another transaction."
        )
