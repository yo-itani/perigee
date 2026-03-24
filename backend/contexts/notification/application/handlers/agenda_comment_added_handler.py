"""Handler for AgendaCommentAdded events."""

from __future__ import annotations

import logging

from contexts.notification.domain.notification_message import NotificationMessage
from contexts.notification.domain.notification_sender import NotificationSender
from contexts.notification.domain.notification_setting_repository import (
    NotificationSettingRepository,
)
from contexts.notification.domain.value_objects import NotificationType
from contexts.preparation.domain.events import AgendaCommentAdded
from contexts.preparation.domain.schedule_repository import ScheduleRepository

logger = logging.getLogger(__name__)


class AgendaCommentAddedHandler:
    """Notify the other party when a comment is added to an agenda.

    Uses ``schedule_id`` from the event to look up the schedule and
    determine organizer/counterpart, then notifies the party who is
    not the comment author.
    """

    def __init__(
        self,
        *,
        schedule_repository: ScheduleRepository,
        notification_sender: NotificationSender,
        notification_setting_repository: NotificationSettingRepository,
    ) -> None:
        self._schedule_repo = schedule_repository
        self._sender = notification_sender
        self._setting_repo = notification_setting_repository

    async def __call__(self, event: AgendaCommentAdded) -> None:
        schedule = await self._schedule_repo.get_by_id(event.schedule_id)
        if schedule is None:
            logger.warning(
                "Schedule %s not found for AgendaCommentAdded notification",
                event.schedule_id,
            )
            return

        # Notify the party who did NOT write the comment
        if event.author_id == schedule.organizer_id:
            recipient_id = schedule.counterpart_id
        else:
            recipient_id = schedule.organizer_id

        if not await self._setting_repo.is_enabled(recipient_id):
            return

        message = NotificationMessage(
            notification_type=NotificationType.AGENDA_COMMENT_ADDED,
            title="New comment on agenda",
            body="A new comment has been added to an agenda topic.",
        )
        try:
            await self._sender.send(recipient_id, message)
        except Exception:
            logger.exception(
                "Failed to send AgendaCommentAdded notification to %s",
                recipient_id,
            )
