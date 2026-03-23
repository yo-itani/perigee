from __future__ import annotations

from contexts.record.domain.record import Record
from contexts.record.domain.value_objects import RecordId
from foundation.domain.base_repository import BaseRepository


class RecordRepository(BaseRepository[Record, RecordId]):
    """Repository interface for Record aggregates."""

    pass  # get_by_id + save only
