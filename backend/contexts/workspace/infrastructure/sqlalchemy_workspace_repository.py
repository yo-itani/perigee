from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from contexts.workspace.domain.value_objects import (
    MembershipId,
    MembershipRole,
    WorkspaceId,
)
from contexts.workspace.domain.workspace import Membership, Workspace
from contexts.workspace.domain.workspace_name import WorkspaceName
from contexts.workspace.domain.workspace_repository import WorkspaceRepository
from contexts.workspace.infrastructure.tables import MembershipTable, WorkspaceTable
from foundation.domain.exceptions import OptimisticLockError
from shared.domain.value_objects import UserId


class SqlAlchemyWorkspaceRepository(WorkspaceRepository):
    """SQLAlchemy-based implementation of WorkspaceRepository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, entity_id: WorkspaceId) -> Workspace | None:
        stmt = select(WorkspaceTable).where(WorkspaceTable.id == str(entity_id.value))
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        if row is None:
            return None
        return self._to_entity(row)

    async def save(self, entity: Workspace) -> None:
        existing = await self._session.get(WorkspaceTable, str(entity.id.value))
        if existing is None:
            await self._insert(entity)
        else:
            await self._update(entity, existing)

    async def get_ancestors(self, workspace_id: WorkspaceId) -> list[Workspace]:
        ancestors: list[Workspace] = []
        current_id: str | None = str(workspace_id.value)

        # Load the starting workspace to get its parent_id
        stmt = select(WorkspaceTable).where(WorkspaceTable.id == current_id)
        result = await self._session.execute(stmt)
        start_row = result.scalar_one_or_none()
        if start_row is None:
            return []
        current_id = start_row.parent_id

        visited: set[str] = {str(workspace_id.value)}
        while current_id is not None:
            if current_id in visited:
                break
            visited.add(current_id)
            stmt = select(WorkspaceTable).where(WorkspaceTable.id == current_id)
            result = await self._session.execute(stmt)
            row = result.scalar_one_or_none()
            if row is None:
                break
            ancestors.append(self._to_entity(row))
            current_id = row.parent_id

        return ancestors

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _insert(self, entity: Workspace) -> None:
        workspace_row = WorkspaceTable(
            id=str(entity.id.value),
            name=entity.name.value,
            parent_id=str(entity.parent_id.value) if entity.parent_id else None,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )
        for m in entity.memberships:
            membership_row = MembershipTable(
                id=str(m.id.value),
                workspace_id=str(entity.id.value),
                user_id=str(m.user_id.value),
                role=m.role.value,
                created_at=entity.created_at,
                updated_at=entity.updated_at,
            )
            workspace_row.memberships.append(membership_row)
        self._session.add(workspace_row)
        await self._session.flush()

    async def _update(self, entity: Workspace, existing: WorkspaceTable) -> None:
        if existing.updated_at != entity.updated_at:
            raise OptimisticLockError("Workspace", str(entity.id.value))

        now = datetime.now(UTC)
        existing.name = entity.name.value
        existing.parent_id = str(entity.parent_id.value) if entity.parent_id else None
        existing.updated_at = now

        # Reconcile memberships: build a map of current DB memberships
        existing_membership_map: dict[str, MembershipTable] = {
            m.id: m for m in existing.memberships
        }
        entity_membership_ids: set[str] = set()

        for m in entity.memberships:
            m_id = str(m.id.value)
            entity_membership_ids.add(m_id)
            if m_id in existing_membership_map:
                # Update existing membership
                db_m = existing_membership_map[m_id]
                db_m.user_id = str(m.user_id.value)
                db_m.role = m.role.value
                db_m.updated_at = now
            else:
                # Insert new membership
                new_m = MembershipTable(
                    id=m_id,
                    workspace_id=str(entity.id.value),
                    user_id=str(m.user_id.value),
                    role=m.role.value,
                    created_at=now,
                    updated_at=now,
                )
                existing.memberships.append(new_m)

        # Remove memberships that are no longer in the entity
        for m_id, db_m in existing_membership_map.items():
            if m_id not in entity_membership_ids:
                existing.memberships.remove(db_m)

        await self._session.flush()

    @staticmethod
    def _to_entity(row: WorkspaceTable) -> Workspace:
        memberships = [
            Membership(
                id=MembershipId.from_str(m.id),
                user_id=UserId.from_str(m.user_id),
                _role=MembershipRole(m.role),
            )
            for m in row.memberships
        ]
        return Workspace(
            id=WorkspaceId.from_str(row.id),
            _name=WorkspaceName(row.name),
            _parent_id=WorkspaceId.from_str(row.parent_id) if row.parent_id else None,
            _memberships=memberships,
            created_at=row.created_at,
            _updated_at=row.updated_at,
        )
