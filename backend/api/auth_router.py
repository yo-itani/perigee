"""FastAPI router for authentication endpoints."""

from __future__ import annotations

import re
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_session, get_user_repository
from foundation.auth.csrf import verify_origin
from foundation.auth.login_attempt_repository import LoginAttemptRepository
from foundation.auth.refresh_token_repository import RefreshTokenRepository
from foundation.auth.use_cases.login_use_case import (
    AccountDeactivatedError,
    AccountLockedError,
    InvalidCredentialsError,
    LoginInput,
    LoginUseCase,
)
from foundation.auth.use_cases.logout_use_case import LogoutUseCase
from foundation.auth.use_cases.refresh_use_case import (
    InvalidRefreshTokenError,
    RefreshUseCase,
)
from foundation.auth.use_cases.set_password_use_case import (
    InvalidInvitationTokenError,
    SetPasswordInput,
    SetPasswordUseCase,
)
from shared.domain.user_repository import UserRepository

auth_router = APIRouter(prefix="/auth", tags=["Auth"])

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

_REFRESH_TOKEN_COOKIE = "refresh_token"
_REFRESH_TOKEN_MAX_AGE = 7 * 24 * 60 * 60  # 7 days in seconds


# -- Schemas -------------------------------------------------------------------


class LoginRequest(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        if not _EMAIL_RE.match(v):
            raise ValueError("Invalid email address")
        return v


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class RefreshResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class SetPasswordRequest(BaseModel):
    token: str
    password: str

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class SetPasswordResponse(BaseModel):
    message: str = "Password set successfully"


# -- DI Providers --------------------------------------------------------------


def _get_refresh_token_repo(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> RefreshTokenRepository:
    from foundation.auth.sqlalchemy_refresh_token_repository import (
        SqlAlchemyRefreshTokenRepository,
    )

    return SqlAlchemyRefreshTokenRepository(session)


def _get_login_attempt_repo(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> LoginAttemptRepository:
    from foundation.auth.sqlalchemy_login_attempt_repository import (
        SqlAlchemyLoginAttemptRepository,
    )

    return SqlAlchemyLoginAttemptRepository(session)


def _get_invitation_token_repo(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> object:
    from foundation.auth.invitation_token_repository import InvitationTokenRepository
    from foundation.auth.sqlalchemy_invitation_token_repository import (
        SqlAlchemyInvitationTokenRepository,
    )

    repo: InvitationTokenRepository = SqlAlchemyInvitationTokenRepository(session)
    return repo


# -- Cookie helpers ------------------------------------------------------------


def _set_refresh_cookie(response: Response, token: str, *, debug: bool) -> None:
    """Set the refresh token as an HttpOnly cookie."""
    response.set_cookie(
        key=_REFRESH_TOKEN_COOKIE,
        value=token,
        httponly=True,
        path="/auth",
        max_age=_REFRESH_TOKEN_MAX_AGE,
        samesite="lax",
        secure=not debug,
    )


def _delete_refresh_cookie(response: Response, *, debug: bool) -> None:
    """Delete the refresh token cookie."""
    response.delete_cookie(
        key=_REFRESH_TOKEN_COOKIE,
        path="/auth",
        httponly=True,
        samesite="lax",
        secure=not debug,
    )


# -- Endpoints -----------------------------------------------------------------


@auth_router.post("/login", response_model=LoginResponse)
async def login(
    body: LoginRequest,
    request: Request,
    response: Response,
    user_repo: Annotated[UserRepository, Depends(get_user_repository)],
    refresh_token_repo: Annotated[
        RefreshTokenRepository, Depends(_get_refresh_token_repo)
    ],
    login_attempt_repo: Annotated[
        LoginAttemptRepository, Depends(_get_login_attempt_repo)
    ],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> LoginResponse:
    """Authenticate with email and password."""
    from foundation.config.settings import settings

    ip_address = request.client.host if request.client else "unknown"

    use_case = LoginUseCase(
        user_repo=user_repo,
        refresh_token_repo=refresh_token_repo,
        login_attempt_repo=login_attempt_repo,
        jwt_secret_key=settings.jwt_secret_key,
        access_token_expire_minutes=settings.jwt_access_token_expire_minutes,
        refresh_token_expire_days=settings.jwt_refresh_token_expire_days,
    )

    try:
        output = await use_case.execute(
            LoginInput(
                email=body.email,
                password=body.password,
                ip_address=ip_address,
            )
        )
    except InvalidCredentialsError:
        await session.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        ) from None
    except AccountLockedError:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Account is temporarily locked due to too many failed attempts",
        ) from None
    except AccountDeactivatedError:
        await session.commit()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated",
        ) from None

    await session.commit()

    _set_refresh_cookie(response, output.refresh_token, debug=settings.debug)

    return LoginResponse(access_token=output.access_token)


@auth_router.post("/refresh", response_model=RefreshResponse)
async def refresh(
    request: Request,
    response: Response,
    user_repo: Annotated[UserRepository, Depends(get_user_repository)],
    refresh_token_repo: Annotated[
        RefreshTokenRepository, Depends(_get_refresh_token_repo)
    ],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> RefreshResponse:
    """Refresh the access token using the refresh token cookie."""
    from foundation.config.settings import settings

    verify_origin(request, settings.cors_origins_list)

    raw_token = request.cookies.get(_REFRESH_TOKEN_COOKIE)
    if not raw_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token not found",
        )

    use_case = RefreshUseCase(
        user_repo=user_repo,
        refresh_token_repo=refresh_token_repo,
        jwt_secret_key=settings.jwt_secret_key,
        access_token_expire_minutes=settings.jwt_access_token_expire_minutes,
        refresh_token_expire_days=settings.jwt_refresh_token_expire_days,
    )

    try:
        output = await use_case.execute(raw_token)
    except InvalidRefreshTokenError:
        _delete_refresh_cookie(response, debug=settings.debug)
        await session.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        ) from None

    await session.commit()

    _set_refresh_cookie(response, output.refresh_token, debug=settings.debug)

    return RefreshResponse(access_token=output.access_token)


@auth_router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    response: Response,
    refresh_token_repo: Annotated[
        RefreshTokenRepository, Depends(_get_refresh_token_repo)
    ],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> None:
    """Log out by revoking the refresh token and clearing the cookie."""
    from foundation.config.settings import settings

    verify_origin(request, settings.cors_origins_list)

    raw_token = request.cookies.get(_REFRESH_TOKEN_COOKIE)
    if raw_token:
        use_case = LogoutUseCase(refresh_token_repo=refresh_token_repo)
        await use_case.execute(raw_token)
        await session.commit()

    _delete_refresh_cookie(response, debug=settings.debug)


@auth_router.post("/set-password", response_model=SetPasswordResponse)
async def set_password(
    body: SetPasswordRequest,
    request: Request,
    user_repo: Annotated[UserRepository, Depends(get_user_repository)],
    refresh_token_repo: Annotated[
        RefreshTokenRepository, Depends(_get_refresh_token_repo)
    ],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> SetPasswordResponse:
    """Set password using an invitation token."""
    from foundation.auth.sqlalchemy_invitation_token_repository import (
        SqlAlchemyInvitationTokenRepository,
    )
    from foundation.config.settings import settings

    verify_origin(request, settings.cors_origins_list)

    invitation_token_repo = SqlAlchemyInvitationTokenRepository(session)

    use_case = SetPasswordUseCase(
        user_repo=user_repo,
        invitation_token_repo=invitation_token_repo,
        refresh_token_repo=refresh_token_repo,
    )

    try:
        await use_case.execute(
            SetPasswordInput(token=body.token, password=body.password)
        )
    except InvalidInvitationTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from None

    await session.commit()

    return SetPasswordResponse()
