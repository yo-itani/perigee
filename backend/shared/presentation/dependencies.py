"""DI providers for the shared (User) presentation layer."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from api.dependencies import get_unit_of_work, get_user_repository
from foundation.application.unit_of_work import UnitOfWork
from shared.application.activate_user_use_case import ActivateUserUseCase
from shared.application.create_user_use_case import CreateUserUseCase
from shared.application.deactivate_user_use_case import DeactivateUserUseCase
from shared.application.get_user_detail_query_service import GetUserDetailQueryService
from shared.application.list_users_query_service import ListUsersQueryService
from shared.application.update_my_profile_use_case import UpdateMyProfileUseCase
from shared.application.update_user_use_case import UpdateUserUseCase
from shared.domain.user_repository import UserRepository


def get_update_my_profile_use_case(
    repo: Annotated[UserRepository, Depends(get_user_repository)],
) -> UpdateMyProfileUseCase:
    return UpdateMyProfileUseCase(user_repo=repo)


def get_list_users_query_service(
    repo: Annotated[UserRepository, Depends(get_user_repository)],
) -> ListUsersQueryService:
    return ListUsersQueryService(user_repo=repo)


def get_create_user_use_case(
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
    repo: Annotated[UserRepository, Depends(get_user_repository)],
) -> CreateUserUseCase:
    return CreateUserUseCase(uow=uow, user_repo=repo)


def get_get_user_detail_query_service(
    repo: Annotated[UserRepository, Depends(get_user_repository)],
) -> GetUserDetailQueryService:
    return GetUserDetailQueryService(user_repo=repo)


def get_update_user_use_case(
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
    repo: Annotated[UserRepository, Depends(get_user_repository)],
) -> UpdateUserUseCase:
    return UpdateUserUseCase(uow=uow, user_repo=repo)


def get_deactivate_user_use_case(
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
    repo: Annotated[UserRepository, Depends(get_user_repository)],
) -> DeactivateUserUseCase:
    return DeactivateUserUseCase(uow=uow, user_repo=repo)


def get_activate_user_use_case(
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
    repo: Annotated[UserRepository, Depends(get_user_repository)],
) -> ActivateUserUseCase:
    return ActivateUserUseCase(uow=uow, user_repo=repo)
