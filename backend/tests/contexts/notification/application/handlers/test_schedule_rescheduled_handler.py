"""Tests for ScheduleRescheduledHandler."""

from __future__ import annotations

from datetime import datetime

from contexts.notification.application.handlers.schedule_rescheduled_handler import (
    ScheduleRescheduledHandler,
)
from contexts.notification.domain.value_objects import NotificationType
from contexts.preparation.domain.events import ScheduleRescheduled
from contexts.preparation.domain.schedule import Schedule
from contexts.preparation.domain.schedule_title import ScheduleTitle
from contexts.preparation.domain.value_objects import ScheduleId
from shared.domain.value_objects import UserId
from tests.contexts.notification.application.handlers.conftest import (
    InMemoryNotificationSettingRepository,
    InMemoryScheduleRepository,
    SpyNotificationSender,
)

NOW = datetime(2026, 3, 25, 10, 0)


def _make_schedule(organizer: UserId, counterpart: UserId) -> Schedule:
    return Schedule.create(
        organizer_id=organizer,
        counterpart_id=counterpart,
        scheduled_at=datetime(2026, 4, 1, 10, 0),
        requested_by=organizer,
        title=ScheduleTitle("Test 1on1"),
        now=NOW,
    )


def _build_handler(
    *,
    schedule_repo: InMemoryScheduleRepository | None = None,
    sender: SpyNotificationSender | None = None,
    setting_repo: InMemoryNotificationSettingRepository | None = None,
) -> tuple[
    ScheduleRescheduledHandler,
    InMemoryScheduleRepository,
    SpyNotificationSender,
]:
    sr = schedule_repo or InMemoryScheduleRepository()
    sn = sender or SpyNotificationSender()
    st = setting_repo or InMemoryNotificationSettingRepository()
    handler = ScheduleRescheduledHandler(
        schedule_repository=sr,
        notification_sender=sn,
        notification_setting_repository=st,
    )
    return handler, sr, sn


class TestScheduleRescheduledHandler:
    """Tests for ScheduleRescheduledHandler."""

    async def test_notifies_counterpart_when_organizer_reschedules(self) -> None:
        organizer = UserId.generate()
        counterpart = UserId.generate()
        schedule = _make_schedule(organizer, counterpart)
        schedule.collect_events()

        handler, sr, sn = _build_handler()
        sr.add(schedule)

        event = ScheduleRescheduled(
            schedule_id=schedule.id,
            organizer_id=organizer,
            counterpart_id=counterpart,
            new_proposed_at=datetime(2026, 4, 2, 10, 0),
            requested_by=organizer,
            occurred_at=NOW,
        )
        await handler(event)

        assert sn.sent_recipient_ids == [counterpart]
        assert sn.sent[0][1].notification_type == NotificationType.SCHEDULE_RESCHEDULED

    async def test_notifies_organizer_when_counterpart_reschedules(self) -> None:
        organizer = UserId.generate()
        counterpart = UserId.generate()
        schedule = _make_schedule(organizer, counterpart)
        schedule.collect_events()

        handler, sr, sn = _build_handler()
        sr.add(schedule)

        event = ScheduleRescheduled(
            schedule_id=schedule.id,
            organizer_id=organizer,
            counterpart_id=counterpart,
            new_proposed_at=datetime(2026, 4, 2, 10, 0),
            requested_by=counterpart,
            occurred_at=NOW,
        )
        await handler(event)

        assert sn.sent_recipient_ids == [organizer]

    async def test_skips_when_notification_disabled(self) -> None:
        organizer = UserId.generate()
        counterpart = UserId.generate()
        schedule = _make_schedule(organizer, counterpart)
        schedule.collect_events()

        setting_repo = InMemoryNotificationSettingRepository(
            disabled_users={counterpart}
        )
        handler, sr, sn = _build_handler(setting_repo=setting_repo)
        sr.add(schedule)

        event = ScheduleRescheduled(
            schedule_id=schedule.id,
            organizer_id=organizer,
            counterpart_id=counterpart,
            new_proposed_at=datetime(2026, 4, 2, 10, 0),
            requested_by=organizer,
            occurred_at=NOW,
        )
        await handler(event)

        assert sn.sent == []

    async def test_logs_on_schedule_not_found(self) -> None:
        handler, _sr, sn = _build_handler()

        event = ScheduleRescheduled(
            schedule_id=ScheduleId.generate(),
            organizer_id=UserId.generate(),
            counterpart_id=UserId.generate(),
            new_proposed_at=datetime(2026, 4, 2, 10, 0),
            requested_by=UserId.generate(),
            occurred_at=NOW,
        )
        await handler(event)

        assert sn.sent == []

    async def test_does_not_propagate_send_failure(self) -> None:
        organizer = UserId.generate()
        counterpart = UserId.generate()
        schedule = _make_schedule(organizer, counterpart)
        schedule.collect_events()

        sender = SpyNotificationSender(fail_for={counterpart})
        handler, sr, _sn = _build_handler(sender=sender)
        sr.add(schedule)

        event = ScheduleRescheduled(
            schedule_id=schedule.id,
            organizer_id=organizer,
            counterpart_id=counterpart,
            new_proposed_at=datetime(2026, 4, 2, 10, 0),
            requested_by=organizer,
            occurred_at=NOW,
        )
        await handler(event)
