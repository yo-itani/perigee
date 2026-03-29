from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from contexts.preparation.domain.schedule import Schedule
from contexts.preparation.domain.schedule_title import ScheduleTitle
from contexts.preparation.domain.value_objects import (
    ConfirmationResolution,
    ScheduleId,
    ScheduleStatus,
)
from contexts.preparation.infrastructure.sqlalchemy_schedule_repository import (
    SqlAlchemyScheduleRepository,
)
from shared.domain.value_objects import UserId
from tests.helpers import create_test_user

pytestmark = pytest.mark.integration

NOW = datetime(2026, 4, 1, 10, 0, tzinfo=UTC)
SCHEDULED_AT = datetime(2026, 4, 10, 14, 0, tzinfo=UTC)


def _make_schedule(
    *,
    organizer_id: UserId,
    counterpart_id: UserId,
    title: str = "Weekly 1on1",
    scheduled_at: datetime = SCHEDULED_AT,
    now: datetime = NOW,
) -> Schedule:
    return Schedule.create(
        organizer_id=organizer_id,
        counterpart_id=counterpart_id,
        scheduled_at=scheduled_at,
        requested_by=organizer_id,
        title=ScheduleTitle(title),
        now=now,
    )


class TestSaveAndGetById:
    """save() -> get_by_id() round-trip."""

    async def test_save_and_restore_new_schedule(self, session: AsyncSession) -> None:
        repo = SqlAlchemyScheduleRepository(session)
        org = await create_test_user(session)
        cp = await create_test_user(session)

        schedule = _make_schedule(organizer_id=org, counterpart_id=cp)
        await repo.save(schedule)
        await session.commit()

        loaded = await repo.get_by_id(schedule.id)

        assert loaded is not None
        assert loaded.id == schedule.id
        assert loaded.organizer_id == org
        assert loaded.counterpart_id == cp
        assert loaded.title == ScheduleTitle("Weekly 1on1")
        assert loaded.scheduled_at == SCHEDULED_AT
        assert loaded.status == ScheduleStatus.REQUESTED
        assert loaded.schedule_group_id is None
        assert len(loaded.confirmation_requests) == 1

        cr = loaded.confirmation_requests[0]
        assert cr.requested_by == org
        assert cr.resolution == ConfirmationResolution.PENDING
        assert cr.resolved_by is None

    async def test_get_by_id_returns_none_for_missing(
        self, session: AsyncSession
    ) -> None:
        repo = SqlAlchemyScheduleRepository(session)
        result = await repo.get_by_id(ScheduleId.generate())
        assert result is None


class TestUpdateScalarFields:
    """save() with scalar field changes."""

    async def test_update_title_and_status(self, session: AsyncSession) -> None:
        repo = SqlAlchemyScheduleRepository(session)
        org = await create_test_user(session)
        cp = await create_test_user(session)

        schedule = _make_schedule(organizer_id=org, counterpart_id=cp)
        await repo.save(schedule)
        await session.commit()

        # Confirm the schedule
        confirm_time = datetime(2026, 4, 2, 10, 0, tzinfo=UTC)
        schedule.confirm(actor_id=cp, now=confirm_time)
        await repo.save(schedule)
        await session.commit()

        loaded = await repo.get_by_id(schedule.id)
        assert loaded is not None
        assert loaded.status == ScheduleStatus.CONFIRMED
        cr = loaded.confirmation_requests[0]
        assert cr.resolution == ConfirmationResolution.APPROVED
        assert cr.resolved_by == cp


class TestConfirmationRequestReconciliation:
    """save() with child entity (ConfirmationRequest) add/update."""

    async def test_reschedule_adds_new_confirmation_request(
        self, session: AsyncSession
    ) -> None:
        repo = SqlAlchemyScheduleRepository(session)
        org = await create_test_user(session)
        cp = await create_test_user(session)

        schedule = _make_schedule(organizer_id=org, counterpart_id=cp)
        await repo.save(schedule)
        await session.commit()

        # Reschedule by organizer
        new_time = datetime(2026, 4, 15, 14, 0, tzinfo=UTC)
        reschedule_now = datetime(2026, 4, 3, 10, 0, tzinfo=UTC)
        schedule.reschedule(actor_id=org, new_proposed_at=new_time, now=reschedule_now)
        await repo.save(schedule)
        await session.commit()

        loaded = await repo.get_by_id(schedule.id)
        assert loaded is not None
        assert len(loaded.confirmation_requests) == 2
        assert loaded.status == ScheduleStatus.REQUESTED

        # First request should be superseded (same actor reschedules)
        resolutions = {cr.resolution for cr in loaded.confirmation_requests}
        assert ConfirmationResolution.SUPERSEDED in resolutions
        assert ConfirmationResolution.PENDING in resolutions

    async def test_multiple_confirmation_requests_round_trip(
        self, session: AsyncSession
    ) -> None:
        repo = SqlAlchemyScheduleRepository(session)
        org = await create_test_user(session)
        cp = await create_test_user(session)

        schedule = _make_schedule(organizer_id=org, counterpart_id=cp)
        # Confirm
        schedule.confirm(actor_id=cp, now=datetime(2026, 4, 2, 10, 0, tzinfo=UTC))
        # Reschedule by counterpart
        schedule.reschedule(
            actor_id=cp,
            new_proposed_at=datetime(2026, 4, 20, 14, 0, tzinfo=UTC),
            now=datetime(2026, 4, 5, 10, 0, tzinfo=UTC),
        )
        await repo.save(schedule)
        await session.commit()

        loaded = await repo.get_by_id(schedule.id)
        assert loaded is not None
        assert len(loaded.confirmation_requests) == 2

        # First: approved, Second: pending
        sorted_crs = sorted(loaded.confirmation_requests, key=lambda x: x.created_at)
        assert sorted_crs[0].resolution == ConfirmationResolution.APPROVED
        assert sorted_crs[1].resolution == ConfirmationResolution.PENDING


class TestAlembicMigration:
    """Verify Alembic upgrade/downgrade with preparation tables."""

    async def test_upgrade_and_downgrade(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Run Alembic upgrade to head then downgrade to base."""
        import os

        from alembic import command
        from alembic.config import Config
        from sqlalchemy import text

        monkeypatch.setenv("PERIGEE_DB_NAME", "perigee_test")
        import sys

        from foundation.config import settings as settings_mod
        from foundation.config.settings import Settings

        patched_settings = Settings()
        monkeypatch.setattr(settings_mod, "settings", patched_settings)
        # Remove migrations.env from module cache so Alembic re-imports it
        # fresh, picking up the patched settings.  Importing it here would
        # fail because alembic.context.config is only available during an
        # Alembic command execution.
        sys.modules.pop("migrations.env", None)

        alembic_cfg = Config(
            os.path.join(
                os.path.dirname(__file__),
                "../../../../alembic.ini",
            )
        )
        alembic_cfg.set_main_option("script_location", "migrations")

        # Drop all tables to start from clean state
        async with session_factory() as s:
            from foundation.db.base import Base

            conn = await s.connection()
            await conn.run_sync(Base.metadata.drop_all)
            await s.execute(text("DROP TABLE IF EXISTS alembic_version"))
            await s.commit()

        # Run Alembic commands in a separate thread because
        # migrations/env.py uses asyncio.run() which cannot be called
        # from an already-running event loop.
        import asyncio

        loop = asyncio.get_event_loop()

        try:
            # Upgrade to head
            await loop.run_in_executor(None, command.upgrade, alembic_cfg, "head")

            # Verify preparation tables exist
            async with session_factory() as s:
                result = await s.execute(text("SHOW TABLES"))
                tables = {row[0] for row in result.fetchall()}
                assert "schedules" in tables
                assert "confirmation_requests" in tables
                assert "schedule_groups" in tables
                assert "schedule_group_agenda_templates" in tables
                assert "templates" in tables
                assert "template_default_counterparts" in tables
                assert "template_agenda_templates" in tables

            # Downgrade to base
            await loop.run_in_executor(None, command.downgrade, alembic_cfg, "base")

            async with session_factory() as s:
                result = await s.execute(text("SHOW TABLES"))
                tables = {row[0] for row in result.fetchall()}
                assert "schedules" not in tables
                assert "confirmation_requests" not in tables
        finally:
            # Always re-create tables so session-scoped fixture teardown works,
            # even if upgrade/downgrade failed.
            async with session_factory() as s:
                from foundation.db.base import Base

                await s.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
                conn = await s.connection()
                await conn.run_sync(Base.metadata.drop_all)
                await s.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
                await s.execute(text("DROP TABLE IF EXISTS alembic_version"))
                conn2 = await s.connection()
                await conn2.run_sync(Base.metadata.create_all)
                await s.commit()
