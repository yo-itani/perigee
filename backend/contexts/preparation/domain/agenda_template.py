from __future__ import annotations

from dataclasses import dataclass

from contexts.preparation.domain.topic import Topic


@dataclass(frozen=True)
class AgendaTemplate:
    """Value object: a topic name template for agenda items.

    Used by both ScheduleGroup and Template to define agenda topics
    that will be expanded into Agenda entities when Schedules are created.
    Order is expressed by position in the containing list.

    Delegates topic validation to the Topic value object.
    """

    topic: Topic

    def __init__(self, topic: str) -> None:
        object.__setattr__(self, "topic", Topic(topic))

    def __str__(self) -> str:
        return str(self.topic)
