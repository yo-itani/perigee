from __future__ import annotations

from datetime import datetime

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from contexts.workspace.domain.value_objects import (
    MembershipRole,
    WorkspaceId,
)
from contexts.workspace.domain.workspace import Workspace
from contexts.workspace.domain.workspace_name import WorkspaceName
from contexts.workspace.infrastructure.sqlalchemy_workspace_repository import (
    SqlAlchemyWorkspaceRepository,
)
from foundation.domain.exceptions import OptimisticLockError
from shared.domain.value_objects import UserId
from shared.infrastructure.tables import UserTable

pytestmark = pytest.mark.integration


async def _create_user(session: AsyncSession) -> UserId:
    """Insert a user row and return its UserId (needed for FK constraints)."""
    user_id = UserId.generate()
    session.add(UserTable(id=str(user_id.value)))
    await session.flush()
    return user_id


def _make_workspace(
    *,
    name: str = "Engineering",
    parent_id: WorkspaceId | None = None,
    now: datetime | None = None,
) -> Workspace:
    return Workspace.create(
        name=WorkspaceName(name),
        parent_id=parent_id,
        now=now or datetime(2026, 3, 20, 10, 0),
    )


class TestSaveAndGetById:
    """save() -> get_by_id() round-trip including Membership."""

    async def test_save_and_restore_workspace_with_memberships(
        self, session: AsyncSession
    ) -> None:
        repo = SqlAlchemyWorkspaceRepository(session)
        user_id = await _create_user(session)

        ws = _make_workspace(name="Team Alpha")
        ws.add_member(
            user_id=user_id,
            role=MembershipRole.CAPTAIN,
            now=datetime(2026, 3, 20, 11, 0),
        )
        await repo.save(ws)
        await session.commit()

        loaded = await repo.get_by_id(ws.id)

        assert loaded is not None
        assert loaded.id == ws.id
        assert loaded.name == WorkspaceName("Team Alpha")
        assert loaded.parent_id is None
        assert len(loaded.memberships) == 1
        assert loaded.memberships[0].user_id == user_id
        assert loaded.memberships[0].role == MembershipRole.CAPTAIN


class TestOptimisticLock:
    """Optimistic lock using updated_at."""

    async def test_successive_saves_succeed(self, session: AsyncSession) -> None:
        """Normal consecutive save should succeed (updated_at is synced)."""
        repo = SqlAlchemyWorkspaceRepository(session)

        ws = _make_workspace(name="V1")
        await repo.save(ws)
        await session.commit()

        ws.rename(new_name=WorkspaceName("V2"), now=datetime(2026, 3, 20, 12, 0))
        await repo.save(ws)
        await session.commit()

        ws.rename(new_name=WorkspaceName("V3"), now=datetime(2026, 3, 20, 13, 0))
        await repo.save(ws)
        await session.commit()

        loaded = await repo.get_by_id(ws.id)
        assert loaded is not None
        assert loaded.name == WorkspaceName("V3")

    async def test_stale_entity_raises_optimistic_lock_error(
        self,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        """When another transaction updates first, the stale save must fail."""
        # Session 1: create workspace
        async with session_factory() as s1:
            repo1 = SqlAlchemyWorkspaceRepository(s1)
            ws = _make_workspace(name="Original")
            await repo1.save(ws)
            await s1.commit()
            ws_id = ws.id

        # Session 2: load and update
        async with session_factory() as s2:
            repo2 = SqlAlchemyWorkspaceRepository(s2)
            ws_s2 = await repo2.get_by_id(ws_id)
            assert ws_s2 is not None
            ws_s2.rename(
                new_name=WorkspaceName("Updated by S2"),
                now=datetime(2026, 3, 20, 14, 0),
            )
            await repo2.save(ws_s2)
            await s2.commit()

        # Session 3: load with stale data from session 1's view and try to save
        async with session_factory() as s3:
            repo3 = SqlAlchemyWorkspaceRepository(s3)
            # Simulate stale entity: load fresh then manually set old updated_at
            ws_stale = await repo3.get_by_id(ws_id)
            assert ws_stale is not None
            # Overwrite updated_at with the original (stale) value
            ws_stale._updated_at = ws.updated_at
            ws_stale.rename(
                new_name=WorkspaceName("Stale update"),
                now=datetime(2026, 3, 20, 15, 0),
            )
            with pytest.raises(OptimisticLockError):
                await repo3.save(ws_stale)


class TestGetAncestors:
    """get_ancestors() traversal."""

    async def test_returns_parent_and_grandparent(self, session: AsyncSession) -> None:
        repo = SqlAlchemyWorkspaceRepository(session)

        grandparent = _make_workspace(name="Company")
        await repo.save(grandparent)

        parent = _make_workspace(name="Division", parent_id=grandparent.id)
        await repo.save(parent)

        child = _make_workspace(name="Team", parent_id=parent.id)
        await repo.save(child)
        await session.commit()

        ancestors = await repo.get_ancestors(child.id)

        assert len(ancestors) == 2
        ancestor_ids = [a.id for a in ancestors]
        assert ancestor_ids == [parent.id, grandparent.id]

    async def test_missing_parent_stops_traversal(self, session: AsyncSession) -> None:
        """If parent_id references a non-existent workspace, traversal stops."""
        repo = SqlAlchemyWorkspaceRepository(session)

        missing_parent_id = WorkspaceId.generate()
        child = _make_workspace(name="Orphan", parent_id=missing_parent_id)
        # Temporarily disable FK checks to insert orphan row
        await session.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
        await session.execute(
            text(
                "INSERT INTO workspaces (id, name, parent_id, created_at, updated_at) "
                "VALUES (:id, :name, :parent_id, :created_at, :updated_at)"
            ),
            {
                "id": str(child.id.value),
                "name": "Orphan",
                "parent_id": str(missing_parent_id.value),
                "created_at": child.created_at,
                "updated_at": child.updated_at,
            },
        )
        await session.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
        await session.commit()

        ancestors = await repo.get_ancestors(child.id)
        assert ancestors == []

    async def test_circular_reference_does_not_loop_forever(
        self, session: AsyncSession
    ) -> None:
        """Cycle in parent chain should be broken by visited-set guard."""
        repo = SqlAlchemyWorkspaceRepository(session)

        ws_a = _make_workspace(name="A")
        ws_b = _make_workspace(name="B", parent_id=ws_a.id)

        await repo.save(ws_a)
        await repo.save(ws_b)
        await session.commit()

        # Create a cycle: A -> B -> A via raw SQL to bypass domain validation
        await session.execute(
            text("UPDATE workspaces SET parent_id = :pid WHERE id = :wid"),
            {"pid": str(ws_b.id.value), "wid": str(ws_a.id.value)},
        )
        await session.commit()

        # Should terminate without infinite loop
        ancestors = await repo.get_ancestors(ws_b.id)
        ancestor_ids = {a.id for a in ancestors}
        # A is B's parent; A's parent is B (cycle) -> visited guard stops
        assert ws_a.id in ancestor_ids
        assert len(ancestors) == 1


class TestAlembicMigration:
    """Verify Alembic upgrade/downgrade executes without error."""

    async def test_upgrade_and_downgrade(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Run Alembic upgrade to head then downgrade to base."""
        import os

        from alembic import command
        from alembic.config import Config

        # Point Alembic env.py (which reads settings.database_url) to perigee_test.
        # pydantic-settings reads env vars, so override PERIGEE_DB_NAME.
        monkeypatch.setenv("PERIGEE_DB_NAME", "perigee_test")
        # Force settings to re-read: replace the module-level singleton
        from foundation.config import settings as settings_mod
        from foundation.config.settings import Settings

        patched_settings = Settings()
        monkeypatch.setattr(settings_mod, "settings", patched_settings)
        # Also patch the reference used by migrations/env.py
        import migrations.env as mig_env_mod

        monkeypatch.setattr(mig_env_mod, "settings", patched_settings)

        alembic_cfg = Config(
            os.path.join(
                os.path.dirname(__file__),
                "../../../../alembic.ini",
            )
        )
        alembic_cfg.set_main_option("script_location", "migrations")

        # First drop all tables to start from a clean state
        async with session_factory() as s:
            from foundation.db.base import Base

            conn = await s.connection()
            await conn.run_sync(Base.metadata.drop_all)
            await s.execute(text("DROP TABLE IF EXISTS alembic_version"))
            await s.commit()

        # Upgrade to head
        command.upgrade(alembic_cfg, "head")

        # Verify tables exist
        async with session_factory() as s:
            result = await s.execute(text("SHOW TABLES"))
            tables = {row[0] for row in result.fetchall()}
            assert "users" in tables
            assert "workspaces" in tables
            assert "memberships" in tables

        # Downgrade to base
        command.downgrade(alembic_cfg, "base")

        # Verify tables are gone (only alembic_version may remain)
        async with session_factory() as s:
            result = await s.execute(text("SHOW TABLES"))
            tables = {row[0] for row in result.fetchall()}
            assert "workspaces" not in tables
            assert "memberships" not in tables

        # Re-create tables via metadata so session-scoped fixture teardown works
        async with session_factory() as s:
            from foundation.db.base import Base

            conn = await s.connection()
            await conn.run_sync(Base.metadata.create_all)
            await s.commit()
