"""Shared DI providers for FastAPI Depends chains."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING, Annotated

from fastapi import Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from foundation.application.unit_of_work import UnitOfWork
from foundation.auth.dependencies import parse_user_id_from_jwt
from foundation.domain.event_dispatcher import EventDispatcher
from shared.domain.system_settings_repository import SystemSettingsRepository
from shared.domain.user import User
from shared.domain.user_repository import UserRepository
from shared.domain.value_objects import UserId

if TYPE_CHECKING:
    from foundation.auth.invitation_token_repository import InvitationTokenRepository
    from foundation.auth.login_attempt_repository import LoginAttemptRepository
    from foundation.auth.refresh_token_repository import RefreshTokenRepository


async def get_session() -> AsyncGenerator[AsyncSession]:
    """Provide a DB session scoped to a single request.

    Uses a lazy import to avoid importing the DB engine at module
    collection time, which would fail without the asyncmy driver.

    All DI providers that need a session should depend on this single
    callable so that repositories and the UoW share the same session.
    """
    from foundation.db.session import async_session_factory

    async with async_session_factory() as session:
        yield session


def get_unit_of_work(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> UnitOfWork:
    """Provide a UnitOfWork backed by the shared request-scoped session."""
    from foundation.infrastructure.sqlalchemy_unit_of_work import SqlAlchemyUnitOfWork

    return SqlAlchemyUnitOfWork(session)


def get_event_dispatcher(request: Request) -> EventDispatcher:
    """Return the app-scope singleton EventDispatcher from app.state."""
    dispatcher: EventDispatcher = request.app.state.event_dispatcher
    return dispatcher


def get_system_settings_repository(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> SystemSettingsRepository:
    """Provide a SystemSettingsRepository backed by the request-scoped session."""
    from shared.infrastructure.sqlalchemy_system_settings_repository import (
        SqlAlchemySystemSettingsRepository,
    )

    return SqlAlchemySystemSettingsRepository(session)


def get_user_repository(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> UserRepository:
    """Provide a UserRepository backed by the request-scoped session."""
    from shared.infrastructure.sqlalchemy_user_repository import (
        SqlAlchemyUserRepository,
    )

    return SqlAlchemyUserRepository(session)


def get_refresh_token_repository(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> RefreshTokenRepository:
    """Provide a RefreshTokenRepository backed by the request-scoped session."""
    from foundation.auth.sqlalchemy_refresh_token_repository import (
        SqlAlchemyRefreshTokenRepository,
    )

    return SqlAlchemyRefreshTokenRepository(session)


def get_login_attempt_repository(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> LoginAttemptRepository:
    """Provide a LoginAttemptRepository backed by the request-scoped session."""
    from foundation.auth.sqlalchemy_login_attempt_repository import (
        SqlAlchemyLoginAttemptRepository,
    )

    return SqlAlchemyLoginAttemptRepository(session)


def get_invitation_token_repository(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> InvitationTokenRepository:
    """Provide an InvitationTokenRepository backed by the request-scoped session."""
    from foundation.auth.sqlalchemy_invitation_token_repository import (
        SqlAlchemyInvitationTokenRepository,
    )

    return SqlAlchemyInvitationTokenRepository(session)


async def get_authenticated_user_id(
    request: Request,
) -> UserId:
    """Extract and validate JWT, returning the authenticated UserId.

    This is a lightweight dependency that does NOT require a DB session,
    so routes fail fast with 401 when the token is missing or invalid.
    """
    return await parse_user_id_from_jwt(request)


async def get_current_user(
    parsed_id: Annotated[UserId, Depends(get_authenticated_user_id)],
    user_repo: Annotated[UserRepository, Depends(get_user_repository)],
) -> User:
    """Authenticate and return the current User via JWT access token."""
    user = await user_repo.get_by_id(parsed_id)
    if user is None:
        raise HTTPException(
            status_code=403,
            detail="User not found",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=403,
            detail="User account is deactivated",
        )
    return user


async def require_admin(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Ensure the current user has admin role."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Admin access required",
        )
    return current_user
