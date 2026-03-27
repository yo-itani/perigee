"""Query service: check whether initial setup has been completed."""

from __future__ import annotations

from dataclasses import dataclass

from shared.domain.user_repository import UserRepository


@dataclass(frozen=True)
class GetSystemStatusOutput:
    is_setup_complete: bool


class GetSystemStatusQueryService:
    """Return whether the system has at least one registered user."""

    def __init__(self, user_repo: UserRepository) -> None:
        self._user_repo = user_repo

    async def execute(self) -> GetSystemStatusOutput:
        count = await self._user_repo.count_all()
        return GetSystemStatusOutput(is_setup_complete=count > 0)
