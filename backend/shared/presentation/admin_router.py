"""FastAPI router for user management endpoints (admin only)."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_session, require_admin
from shared.application.activate_user_use_case import (
    ActivateUserInput,
    ActivateUserUseCase,
)
from shared.application.activate_user_use_case import (
    UserNotFoundError as ActivateUserNotFoundError,
)
from shared.application.create_user_use_case import (
    CreateUserInput,
    CreateUserUseCase,
    EmailAlreadyTakenError,
)
from shared.application.deactivate_user_use_case import (
    DeactivateUserInput,
    DeactivateUserUseCase,
)
from shared.application.deactivate_user_use_case import (
    LastAdminError as DeactivateLastAdminError,
)
from shared.application.deactivate_user_use_case import (
    UserNotFoundError as DeactivateUserNotFoundError,
)
from shared.application.get_user_detail_query_service import (
    GetUserDetailInput,
    GetUserDetailQueryService,
)
from shared.application.get_user_detail_query_service import (
    UserNotFoundError as GetUserNotFoundError,
)
from shared.application.list_users_query_service import (
    ListUsersInput,
    ListUsersQueryService,
)
from shared.application.update_user_use_case import (
    EmailAlreadyTakenError as UpdateEmailAlreadyTakenError,
)
from shared.application.update_user_use_case import (
    LastAdminError as UpdateLastAdminError,
)
from shared.application.update_user_use_case import (
    UpdateUserInput,
    UpdateUserUseCase,
)
from shared.application.update_user_use_case import (
    UserNotFoundError as UpdateUserNotFoundError,
)
from shared.domain.user import User
from shared.domain.value_objects import UserId
from shared.presentation.dependencies import (
    get_activate_user_use_case,
    get_create_user_use_case,
    get_deactivate_user_use_case,
    get_get_user_detail_query_service,
    get_list_users_query_service,
    get_update_user_use_case,
)
from shared.presentation.schemas import (
    CreateUserRequest,
    UpdateUserRequest,
    UserListResponse,
    UserProfileResponse,
)

admin_router = APIRouter(prefix="/users", tags=["User Management"])


def _parse_user_id(raw: str) -> UserId:
    """Parse a user_id path parameter, raising 400 on invalid UUID."""
    try:
        return UserId.from_str(raw)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID format",
        ) from None


@admin_router.get("", response_model=UserListResponse)
async def list_users(
    _admin: Annotated[User, Depends(require_admin)],
    query_service: Annotated[
        ListUsersQueryService, Depends(get_list_users_query_service)
    ],
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=1000)] = 100,
) -> UserListResponse:
    """Return users in the system with pagination."""
    output = await query_service.execute(
        input_dto=ListUsersInput(offset=offset, limit=limit)
    )
    return UserListResponse(
        users=[
            UserProfileResponse(
                id=str(u.id.value),
                name=u.name,
                email=u.email,
                role=u.role,
                is_active=u.is_active,
                slack_user_id=u.slack_user_id,
            )
            for u in output.users
        ],
        total=output.total,
    )


@admin_router.post(
    "", response_model=UserProfileResponse, status_code=status.HTTP_201_CREATED
)
async def create_user(
    body: CreateUserRequest,
    _admin: Annotated[User, Depends(require_admin)],
    use_case: Annotated[CreateUserUseCase, Depends(get_create_user_use_case)],
) -> UserProfileResponse:
    """Create a new user."""
    try:
        output = await use_case.execute(
            input_dto=CreateUserInput(
                name=body.name,
                email=body.email,
                role=body.role,
            )
        )
    except EmailAlreadyTakenError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email address is already in use",
        ) from None
    return UserProfileResponse(
        id=str(output.id.value),
        name=output.name,
        email=output.email,
        role=output.role,
        is_active=output.is_active,
        slack_user_id=output.slack_user_id,
    )


@admin_router.get("/{user_id}", response_model=UserProfileResponse)
async def get_user_detail(
    user_id: str,
    _admin: Annotated[User, Depends(require_admin)],
    query_service: Annotated[
        GetUserDetailQueryService, Depends(get_get_user_detail_query_service)
    ],
) -> UserProfileResponse:
    """Return a single user's detail."""
    try:
        output = await query_service.execute(
            input_dto=GetUserDetailInput(user_id=_parse_user_id(user_id))
        )
    except GetUserNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        ) from None
    return UserProfileResponse(
        id=str(output.id.value),
        name=output.name,
        email=output.email,
        role=output.role,
        is_active=output.is_active,
        slack_user_id=output.slack_user_id,
    )


@admin_router.put("/{user_id}", response_model=UserProfileResponse)
async def update_user(
    user_id: str,
    body: UpdateUserRequest,
    _admin: Annotated[User, Depends(require_admin)],
    use_case: Annotated[UpdateUserUseCase, Depends(get_update_user_use_case)],
) -> UserProfileResponse:
    """Update a user's name, email, and role."""
    try:
        output = await use_case.execute(
            input_dto=UpdateUserInput(
                user_id=_parse_user_id(user_id),
                name=body.name,
                email=body.email,
                role=body.role,
            )
        )
    except UpdateUserNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        ) from None
    except UpdateEmailAlreadyTakenError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email address is already in use",
        ) from None
    except UpdateLastAdminError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot remove admin role from the last active admin",
        ) from None
    return UserProfileResponse(
        id=str(output.id.value),
        name=output.name,
        email=output.email,
        role=output.role,
        is_active=output.is_active,
        slack_user_id=output.slack_user_id,
    )


@admin_router.put("/{user_id}/deactivate", response_model=UserProfileResponse)
async def deactivate_user(
    user_id: str,
    _admin: Annotated[User, Depends(require_admin)],
    use_case: Annotated[DeactivateUserUseCase, Depends(get_deactivate_user_use_case)],
) -> UserProfileResponse:
    """Deactivate a user."""
    try:
        output = await use_case.execute(
            input_dto=DeactivateUserInput(user_id=_parse_user_id(user_id))
        )
    except DeactivateUserNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        ) from None
    except DeactivateLastAdminError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot deactivate the last active admin",
        ) from None
    return UserProfileResponse(
        id=str(output.id.value),
        name=output.name,
        email=output.email,
        role=output.role,
        is_active=output.is_active,
        slack_user_id=output.slack_user_id,
    )


@admin_router.put("/{user_id}/activate", response_model=UserProfileResponse)
async def activate_user(
    user_id: str,
    _admin: Annotated[User, Depends(require_admin)],
    use_case: Annotated[ActivateUserUseCase, Depends(get_activate_user_use_case)],
) -> UserProfileResponse:
    """Activate a deactivated user."""
    try:
        output = await use_case.execute(
            input_dto=ActivateUserInput(user_id=_parse_user_id(user_id))
        )
    except ActivateUserNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        ) from None
    return UserProfileResponse(
        id=str(output.id.value),
        name=output.name,
        email=output.email,
        role=output.role,
        is_active=output.is_active,
        slack_user_id=output.slack_user_id,
    )


class InvitationResponse(BaseModel):
    token: str
    expires_at: datetime


@admin_router.post(
    "/{user_id}/invite",
    response_model=InvitationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_invitation(
    user_id: str,
    _admin: Annotated[User, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> InvitationResponse:
    """Generate an invitation link for a user to set their password."""
    from foundation.auth.sqlalchemy_invitation_token_repository import (
        SqlAlchemyInvitationTokenRepository,
    )
    from foundation.auth.use_cases.create_invitation_use_case import (
        CreateInvitationInput,
        CreateInvitationUseCase,
    )
    from foundation.auth.use_cases.create_invitation_use_case import (
        UserNotFoundError as InvitationUserNotFoundError,
    )
    from shared.infrastructure.sqlalchemy_user_repository import (
        SqlAlchemyUserRepository,
    )

    user_repo = SqlAlchemyUserRepository(session)
    invitation_token_repo = SqlAlchemyInvitationTokenRepository(session)

    use_case = CreateInvitationUseCase(
        user_repo=user_repo,
        invitation_token_repo=invitation_token_repo,
    )

    try:
        output = await use_case.execute(
            CreateInvitationInput(user_id=_parse_user_id(user_id))
        )
    except InvitationUserNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        ) from None

    await session.commit()

    return InvitationResponse(
        token=output.token,
        expires_at=output.expires_at,
    )
