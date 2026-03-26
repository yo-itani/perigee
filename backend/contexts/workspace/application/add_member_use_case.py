"""Use case: Add a member to a workspace."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from contexts.workspace.domain.value_objects import (
    MembershipId,
    MembershipRole,
    WorkspaceId,
)
from contexts.workspace.domain.workspace_repository import WorkspaceRepository
from foundation.application.unit_of_work import UnitOfWork
from foundation.domain.event_dispatcher import EventDispatcher
from shared.domain.events import DomainEvent
from shared.domain.value_objects import UserId


class WorkspaceNotFoundError(Exception):
    """Raised when the specified workspace does not exist."""

    def __init__(self, message: str = "Workspace not found.") -> None:
        super().__init__(message)


@dataclass(frozen=True)
class AddMemberInput:
    """Input DTO for adding a member to a workspace."""

    workspace_id: WorkspaceId
    user_id: UserId
    role: MembershipRole = MembershipRole.MEMBER


@dataclass(frozen=True)
class AddMemberOutput:
    """Output DTO for adding a member to a workspace."""

    membership_id: MembershipId


class AddMemberUseCase:
    """Application service that adds a member to a workspace.

    The user is added with the specified role (defaults to Member).
    Domain layer prevents duplicate memberships.
    """

    def __init__(
        self,
        uow: UnitOfWork,
        workspace_repo: WorkspaceRepository,
        event_dispatcher: EventDispatcher,
    ) -> None:
        self._uow = uow
        self._workspace_repo = workspace_repo
        self._event_dispatcher = event_dispatcher

    async def execute(
        self,
        input_dto: AddMemberInput,
    ) -> AddMemberOutput:
        """Add a member to the workspace and return the membership id.

        Args:
            input_dto: The input containing workspace id, user id, and role.

        Returns:
            Output containing the id of the newly created membership.

        Raises:
            WorkspaceNotFoundError: If the workspace does not exist.
            DuplicateMembershipError: If the user is already a member.
        """
        now = datetime.now(UTC)

        async with self._uow:
            workspace = await self._workspace_repo.get_by_id(input_dto.workspace_id)
            if workspace is None:
                raise WorkspaceNotFoundError()

            membership = workspace.add_member(
                user_id=input_dto.user_id,
                role=input_dto.role,
                now=now,
            )
            await self._workspace_repo.save(workspace)
            events: list[DomainEvent] = list(workspace.collect_events())
            await self._uow.commit()

        await self._event_dispatcher.dispatch(events)

        return AddMemberOutput(membership_id=membership.id)
