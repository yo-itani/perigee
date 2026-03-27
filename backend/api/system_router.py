"""FastAPI router for system setup endpoints (no auth required)."""

from __future__ import annotations

import re
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, field_validator

from api.dependencies import get_unit_of_work, get_user_repository
from foundation.application.unit_of_work import UnitOfWork
from shared.application.get_system_status_query_service import (
    GetSystemStatusOutput,
    GetSystemStatusQueryService,
)
from shared.application.setup_first_user_use_case import (
    SetupAlreadyCompleteError,
    SetupFirstUserInput,
    SetupFirstUserOutput,
    SetupFirstUserUseCase,
)
from shared.domain.user_repository import UserRepository
from shared.domain.value_objects import UserRole

system_router = APIRouter(prefix="/system", tags=["System"])

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


# -- Schemas -------------------------------------------------------------------


class SystemStatusResponse(BaseModel):
    """Response schema for system status."""

    is_setup_complete: bool


class SetupFirstUserRequest(BaseModel):
    """Request schema for first user setup."""

    name: str
    email: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        if not _EMAIL_RE.match(v):
            raise ValueError("Invalid email address")
        return v


class SetupFirstUserResponse(BaseModel):
    """Response schema for first user setup."""

    id: str
    name: str
    email: str
    role: UserRole
    is_active: bool
    slack_user_id: str | None


# -- DI Providers --------------------------------------------------------------


def _get_system_status_query_service(
    repo: Annotated[UserRepository, Depends(get_user_repository)],
) -> GetSystemStatusQueryService:
    return GetSystemStatusQueryService(user_repo=repo)


def _get_setup_first_user_use_case(
    repo: Annotated[UserRepository, Depends(get_user_repository)],
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
) -> SetupFirstUserUseCase:
    return SetupFirstUserUseCase(user_repo=repo, uow=uow)


# -- Endpoints -----------------------------------------------------------------


@system_router.get("/status", response_model=SystemStatusResponse)
async def get_system_status(
    query_service: Annotated[
        GetSystemStatusQueryService,
        Depends(_get_system_status_query_service),
    ],
) -> SystemStatusResponse:
    """Check whether the initial setup has been completed."""
    output: GetSystemStatusOutput = await query_service.execute()
    return SystemStatusResponse(is_setup_complete=output.is_setup_complete)


@system_router.post(
    "/setup",
    response_model=SetupFirstUserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def setup_first_user(
    body: SetupFirstUserRequest,
    use_case: Annotated[
        SetupFirstUserUseCase,
        Depends(_get_setup_first_user_use_case),
    ],
) -> SetupFirstUserResponse:
    """Register the first admin user. Only available when no users exist."""
    try:
        output: SetupFirstUserOutput = await use_case.execute(
            input_dto=SetupFirstUserInput(name=body.name, email=body.email),
        )
    except SetupAlreadyCompleteError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Setup is already complete. Users already exist.",
        ) from None
    return SetupFirstUserResponse(
        id=str(output.id.value),
        name=output.name,
        email=output.email,
        role=output.role,
        is_active=output.is_active,
        slack_user_id=output.slack_user_id,
    )
