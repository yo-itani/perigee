from __future__ import annotations

from dataclasses import dataclass

from contexts.preparation.domain.exceptions import InvalidAgendaTopicError

_AGENDA_TOPIC_MAX_LENGTH = 200


@dataclass(frozen=True)
class AgendaTemplate:
    """Value object: a topic name template for agenda items.

    Used by both ScheduleGroup and Template to define agenda topics
    that will be expanded into Agenda entities when Schedules are created.
    Order is expressed by position in the containing list.

    Invariants:
    - Topic must not be empty (after stripping whitespace).
    - Topic must not contain newlines.
    - Max 200 characters.
    - Leading/trailing whitespace is stripped.
    """

    topic: str

    def __init__(self, topic: str) -> None:
        stripped = topic.strip()
        if not stripped:
            raise InvalidAgendaTopicError("Agenda topic must not be empty.")
        if "\n" in stripped or "\r" in stripped:
            raise InvalidAgendaTopicError("Agenda topic must not contain newlines.")
        if len(stripped) > _AGENDA_TOPIC_MAX_LENGTH:
            raise InvalidAgendaTopicError(
                f"Agenda topic must not exceed {_AGENDA_TOPIC_MAX_LENGTH} characters."
            )
        object.__setattr__(self, "topic", stripped)

    def __str__(self) -> str:
        return self.topic
