from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from contexts.record.domain.events import RetrospectiveAdded
from contexts.record.domain.retrospective_body import RetrospectiveBody
from contexts.record.domain.value_objects import RecordId, RetrospectiveId
from shared.domain.value_objects import UserId

type _RetrospectiveEvent = RetrospectiveAdded


@dataclass
class Retrospective:
    """Aggregate root: a retrospective on a published record.

    Retrospectives can be made by organizer or counterpart.
    Authorization (whether the actor is allowed to add a retrospective)
    is the responsibility of the application layer, not the domain.
    Retrospectives are insert-only (no edit or delete).
    """

    id: RetrospectiveId
    record_id: RecordId
    author_id: UserId
    body: RetrospectiveBody
    created_at: datetime
    _events: list[_RetrospectiveEvent] = field(default_factory=list, repr=False)

    @staticmethod
    def create(
        *,
        record_id: RecordId,
        author_id: UserId,
        body: RetrospectiveBody,
        now: datetime | None = None,
    ) -> Retrospective:
        """Create a new retrospective."""
        retrospective_id = RetrospectiveId.generate()
        ts = now or datetime.now(UTC)
        retrospective = Retrospective(
            id=retrospective_id,
            record_id=record_id,
            author_id=author_id,
            body=body,
            created_at=ts,
        )
        retrospective._events.append(
            RetrospectiveAdded(
                occurred_at=ts,
                retrospective_id=retrospective_id,
                record_id=record_id,
                author_id=author_id,
            )
        )
        return retrospective

    def collect_events(self) -> list[_RetrospectiveEvent]:
        """Return accumulated events and clear the internal list."""
        events = list(self._events)
        self._events.clear()
        return events
