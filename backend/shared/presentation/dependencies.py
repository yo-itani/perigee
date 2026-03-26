"""DI providers for the shared (User) presentation layer."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_session
from shared.application.update_my_profile_use_case import UpdateMyProfileUseCase
from shared.infrastructure.sqlalchemy_user_repository import SqlAlchemyUserRepository


def get_update_my_profile_use_case(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> UpdateMyProfileUseCase:
    repo = SqlAlchemyUserRepository(session)
    return UpdateMyProfileUseCase(user_repo=repo)
