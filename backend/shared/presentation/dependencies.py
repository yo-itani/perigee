"""DI providers for the shared (User) presentation layer."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_session
from shared.application.update_my_profile_use_case import UpdateMyProfileUseCase
from shared.domain.user_repository import UserRepository
from shared.infrastructure.sqlalchemy_user_repository import (
    SqlAlchemyUserRepository,
)


def get_user_repository(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> UserRepository:
    return SqlAlchemyUserRepository(session)


def get_update_my_profile_use_case(
    repo: Annotated[UserRepository, Depends(get_user_repository)],
) -> UpdateMyProfileUseCase:
    return UpdateMyProfileUseCase(user_repo=repo)
