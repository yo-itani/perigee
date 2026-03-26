"""Tests for SendReminderUseCase."""

from __future__ import annotations

from datetime import datetime, timedelta

from contexts.notification.application.send_reminder_use_case import (
    SendReminderUseCase,
)
from contexts.notification.domain.notification_setting import NotificationSetting
from contexts.notification.domain.notification_setting_repository import (
    NotificationSettingRepository,
)
from contexts.notification.domain.reminder_log import ReminderLog
from contexts.notification.domain.reminder_log_repository import ReminderLogRepository
from contexts.notification.domain.value_objects import NotificationType
from contexts.preparation.domain.schedule import Schedule
from contexts.preparation.domain.schedule_title import ScheduleTitle
from contexts.preparation.domain.value_objects import ScheduleId, ScheduleStatus
from shared.domain.value_objects import UserId
from tests.contexts.notification.application.handlers.conftest import (
    InMemoryNotificationSettingRepository,
    InMemoryScheduleRepository,
    SpyNotificationSender,
)

SCHEDULED_AT = datetime(2026, 4, 1, 10, 0)
CREATION_TIME = datetime(2026, 3, 20, 10, 0)


def _make_confirmed_schedule(
    organizer: UserId,
    counterpart: UserId,
    scheduled_at: datetime = SCHEDULED_AT,
) -> Schedule:
    """Create a CONFIRMED schedule for testing."""
    schedule = Schedule.create(
        organizer_id=organizer,
        counterpart_id=counterpart,
        scheduled_at=scheduled_at,
        requested_by=organizer,
        title=ScheduleTitle("Test 1on1"),
        now=CREATION_TIME,
    )
    schedule.confirm(actor_id=counterpart, now=CREATION_TIME)
    schedule.collect_events()
    return schedule


class InMemoryReminderLogRepository(ReminderLogRepository):
    """In-memory stub for ReminderLogRepository."""

    def __init__(self) -> None:
        self._logs: list[ReminderLog] = []

    async def exists(
        self,
        schedule_id: ScheduleId,
        user_id: UserId,
        scheduled_at: datetime,
    ) -> bool:
        return any(
            log.schedule_id == schedule_id
            and log.user_id == user_id
            and log.scheduled_at == scheduled_at
            for log in self._logs
        )

    async def save(self, log: ReminderLog) -> None:
        self._logs.append(log)

    @property
    def saved_logs(self) -> list[ReminderLog]:
        return list(self._logs)


def _build_service(
    *,
    schedule_repo: InMemoryScheduleRepository | None = None,
    setting_repo: NotificationSettingRepository | None = None,
    reminder_log_repo: InMemoryReminderLogRepository | None = None,
    sender: SpyNotificationSender | None = None,
) -> tuple[
    SendReminderUseCase,
    InMemoryScheduleRepository,
    InMemoryReminderLogRepository,
    SpyNotificationSender,
]:
    sr = schedule_repo or InMemoryScheduleRepository()
    st = setting_repo or InMemoryNotificationSettingRepository()
    rl = reminder_log_repo or InMemoryReminderLogRepository()
    sn = sender or SpyNotificationSender()
    service = SendReminderUseCase(
        schedule_repository=sr,
        notification_setting_repository=st,
        reminder_log_repository=rl,
        notification_sender=sn,
    )
    return service, sr, rl, sn


class TestSendReminderUseCase:
    """Tests for SendReminderUseCase reminder logic."""

    async def test_sends_reminder_to_both_participants(self) -> None:
        """Both organizer and counterpart receive reminders."""
        organizer = UserId.generate()
        counterpart = UserId.generate()
        schedule = _make_confirmed_schedule(organizer, counterpart)

        service, sr, rl, sn = _build_service()
        sr.add(schedule)

        # Default reminder is 30 minutes before; now = scheduled_at - 25 min
        now = SCHEDULED_AT - timedelta(minutes=25)
        await service.execute(now)

        assert len(sn.sent) == 2
        sent_ids = {r for r, _ in sn.sent}
        assert sent_ids == {organizer, counterpart}
        assert all(
            msg.notification_type == NotificationType.REMINDER for _, msg in sn.sent
        )

    async def test_does_not_send_before_reminder_window(self) -> None:
        """Reminders are not sent if the window has not opened yet."""
        organizer = UserId.generate()
        counterpart = UserId.generate()
        schedule = _make_confirmed_schedule(organizer, counterpart)

        service, sr, _rl, sn = _build_service()
        sr.add(schedule)

        # Default 30 min reminder; now = scheduled_at - 35 min (too early)
        now = SCHEDULED_AT - timedelta(minutes=35)
        await service.execute(now)

        assert sn.sent == []

    async def test_does_not_send_for_past_schedule(self) -> None:
        """Schedules where scheduled_at <= now are excluded."""
        organizer = UserId.generate()
        counterpart = UserId.generate()
        schedule = _make_confirmed_schedule(organizer, counterpart)

        service, sr, _rl, sn = _build_service()
        sr.add(schedule)

        # now == scheduled_at (boundary: scheduled_at > now must be strict)
        now = SCHEDULED_AT
        await service.execute(now)

        assert sn.sent == []

    async def test_does_not_send_when_disabled(self) -> None:
        """Users with is_enabled=false do not get reminders."""
        organizer = UserId.generate()
        counterpart = UserId.generate()
        schedule = _make_confirmed_schedule(organizer, counterpart)

        setting_repo = InMemoryNotificationSettingRepository(
            disabled_users={organizer, counterpart}
        )
        service, sr, _rl, sn = _build_service(setting_repo=setting_repo)
        sr.add(schedule)

        now = SCHEDULED_AT - timedelta(minutes=25)
        await service.execute(now)

        assert sn.sent == []

    async def test_prevents_duplicate_send(self) -> None:
        """Second run does not re-send if ReminderLog exists."""
        organizer = UserId.generate()
        counterpart = UserId.generate()
        schedule = _make_confirmed_schedule(organizer, counterpart)

        service, sr, rl, sn = _build_service()
        sr.add(schedule)

        now = SCHEDULED_AT - timedelta(minutes=25)
        await service.execute(now)
        assert len(sn.sent) == 2

        # Run again - should not send duplicates
        await service.execute(now)
        assert len(sn.sent) == 2

    async def test_reminder_log_saved_for_each_recipient(self) -> None:
        """A ReminderLog is created for each sent reminder."""
        organizer = UserId.generate()
        counterpart = UserId.generate()
        schedule = _make_confirmed_schedule(organizer, counterpart)

        service, sr, rl, _sn = _build_service()
        sr.add(schedule)

        now = SCHEDULED_AT - timedelta(minutes=25)
        await service.execute(now)

        assert len(rl.saved_logs) == 2
        log_user_ids = {log.user_id for log in rl.saved_logs}
        assert log_user_ids == {organizer, counterpart}
        for log in rl.saved_logs:
            assert log.schedule_id == schedule.id
            assert log.scheduled_at == SCHEDULED_AT
            assert log.reminder_minutes_before == 30  # default

    async def test_reschedule_allows_new_reminder(self) -> None:
        """After reschedule to new datetime, reminders can be sent again."""
        organizer = UserId.generate()
        counterpart = UserId.generate()
        schedule = _make_confirmed_schedule(organizer, counterpart)

        rl = InMemoryReminderLogRepository()
        service, sr, rl, sn = _build_service(reminder_log_repo=rl)
        sr.add(schedule)

        # Send first reminder
        now = SCHEDULED_AT - timedelta(minutes=25)
        await service.execute(now)
        assert len(sn.sent) == 2

        # Pre-populate a ReminderLog for the OLD scheduled_at
        # (simulating that the first reminders were already sent)
        # The schedule is rescheduled to a new datetime
        new_scheduled_at = datetime(2026, 4, 5, 14, 0)
        schedule.reschedule(
            actor_id=organizer,
            new_proposed_at=new_scheduled_at,
            now=now,
        )
        schedule.confirm(actor_id=counterpart, now=now)
        schedule.collect_events()

        # Now the schedule is at a new datetime
        now2 = new_scheduled_at - timedelta(minutes=25)
        await service.execute(now2)

        # Should have 4 total sends: 2 for old + 2 for new
        assert len(sn.sent) == 4

    async def test_respects_per_user_reminder_minutes(self) -> None:
        """Each user's individual reminder_minutes_before is respected."""
        organizer = UserId.generate()
        counterpart = UserId.generate()
        schedule = _make_confirmed_schedule(organizer, counterpart)

        # Organizer has 60 min reminder, counterpart has default 30 min
        setting_repo = _PerUserSettingRepository({organizer: 60})
        service, sr, _rl, sn = _build_service(setting_repo=setting_repo)
        sr.add(schedule)

        # At 45 min before: organizer window open (60 min), counterpart not yet (30 min)
        now = SCHEDULED_AT - timedelta(minutes=45)
        await service.execute(now)

        assert len(sn.sent) == 1
        assert sn.sent_recipient_ids == [organizer]

    async def test_does_not_send_for_requested_schedule(self) -> None:
        """REQUESTED schedules are not eligible for reminders."""
        organizer = UserId.generate()
        counterpart = UserId.generate()
        # Create but do NOT confirm
        schedule = Schedule.create(
            organizer_id=organizer,
            counterpart_id=counterpart,
            scheduled_at=SCHEDULED_AT,
            requested_by=organizer,
            title=ScheduleTitle("Test 1on1"),
            now=CREATION_TIME,
        )
        schedule.collect_events()
        assert schedule.status == ScheduleStatus.REQUESTED

        service, sr, _rl, sn = _build_service()
        sr.add(schedule)

        now = SCHEDULED_AT - timedelta(minutes=25)
        await service.execute(now)

        assert sn.sent == []

    async def test_does_not_send_for_cancelled_schedule(self) -> None:
        """CANCELLED schedules are not eligible for reminders."""
        organizer = UserId.generate()
        counterpart = UserId.generate()
        schedule = _make_confirmed_schedule(organizer, counterpart)
        schedule.cancel(actor_id=organizer, now=CREATION_TIME)
        schedule.collect_events()
        assert schedule.status == ScheduleStatus.CANCELLED

        service, sr, _rl, sn = _build_service()
        sr.add(schedule)

        now = SCHEDULED_AT - timedelta(minutes=25)
        await service.execute(now)

        assert sn.sent == []

    async def test_send_failure_does_not_block_other_participants(self) -> None:
        """If sending fails for one user, the other still gets notified."""
        organizer = UserId.generate()
        counterpart = UserId.generate()
        schedule = _make_confirmed_schedule(organizer, counterpart)

        sender = SpyNotificationSender(fail_for={organizer})
        service, sr, rl, _sn = _build_service(sender=sender)
        sr.add(schedule)

        now = SCHEDULED_AT - timedelta(minutes=25)
        await service.execute(now)

        # Counterpart should still receive notification
        assert len(sender.sent) == 1
        assert sender.sent_recipient_ids == [counterpart]
        # Only counterpart's log should be saved
        assert len(rl.saved_logs) == 1
        assert rl.saved_logs[0].user_id == counterpart

    async def test_boundary_now_equals_scheduled_at_minus_reminder(self) -> None:
        """Exact boundary: now == scheduled_at - reminder_minutes sends."""
        organizer = UserId.generate()
        counterpart = UserId.generate()
        schedule = _make_confirmed_schedule(organizer, counterpart)

        service, sr, _rl, sn = _build_service()
        sr.add(schedule)

        # Exactly at the reminder threshold
        now = SCHEDULED_AT - timedelta(minutes=30)
        await service.execute(now)

        assert len(sn.sent) == 2


class _PerUserSettingRepository(NotificationSettingRepository):
    """Test helper that returns custom reminder minutes per user."""

    def __init__(self, custom_minutes: dict[UserId, int]) -> None:
        self._custom = custom_minutes

    async def get_by_user_id(self, user_id: UserId) -> NotificationSetting | None:
        if user_id in self._custom:
            return NotificationSetting.create(
                user_id=user_id,
                reminder_minutes_before=self._custom[user_id],
                is_enabled=True,
            )
        return None  # default

    async def save(self, entity: NotificationSetting) -> None:
        pass
