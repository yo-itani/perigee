"""FastAPI router for user profile endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from api.dependencies import get_current_user
from shared.application.get_my_profile_query_service import GetMyProfileQueryService
from shared.application.update_my_profile_use_case import (
    EmailAlreadyTakenError,
    UpdateMyProfileInput,
    UpdateMyProfileUseCase,
)
from shared.domain.user import User
from shared.presentation.dependencies import get_update_my_profile_use_case
from shared.presentation.schemas import UpdateMyProfileRequest, UserProfileResponse

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserProfileResponse)
async def get_my_profile(
    current_user: Annotated[User, Depends(get_current_user)],
) -> UserProfileResponse:
    """Return the current user's profile."""
    service = GetMyProfileQueryService()
    output = service.execute(current_user)
    return UserProfileResponse(
        id=str(output.id.value),
        name=output.name,
        email=output.email,
        role=output.role,
        is_active=output.is_active,
        slack_user_id=output.slack_user_id,
    )


@router.put("/me", response_model=UserProfileResponse)
async def update_my_profile(
    body: UpdateMyProfileRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    use_case: Annotated[
        UpdateMyProfileUseCase, Depends(get_update_my_profile_use_case)
    ],
) -> UserProfileResponse:
    """Update the current user's name and email."""
    try:
        output = await use_case.execute(
            input_dto=UpdateMyProfileInput(
                name=body.name,
                email=body.email,
            ),
            current_user=current_user,
        )
    except EmailAlreadyTakenError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email address is already in use",
        ) from None
    # Reload user to get full profile after update
    return UserProfileResponse(
        id=str(output.id.value),
        name=output.name,
        email=output.email,
        role=current_user.role,
        is_active=current_user.is_active,
        slack_user_id=current_user.slack_user_id,
    )
