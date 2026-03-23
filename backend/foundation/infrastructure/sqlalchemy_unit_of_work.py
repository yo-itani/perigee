from __future__ import annotations

from types import TracebackType

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from foundation.application.unit_of_work import UnitOfWork


class SqlAlchemyUnitOfWork(UnitOfWork):
    """Unit of Work implementation backed by a SQLAlchemy ``AsyncSession``.

    Usage::

        uow = SqlAlchemyUnitOfWork(session_factory)
        async with uow:
            # use uow.session to interact with repositories
            await uow.commit()

    On context-manager exit, any uncommitted changes are rolled back
    automatically if an exception propagates.
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory
        self._session: AsyncSession | None = None

    @property
    def session(self) -> AsyncSession:
        """Return the active session.

        Raises ``RuntimeError`` if accessed outside the context manager.
        """
        if self._session is None:
            raise RuntimeError(
                "SqlAlchemyUnitOfWork must be used as an async context manager."
            )
        return self._session

    async def commit(self) -> None:
        """Commit the current database transaction."""
        await self.session.commit()

    async def rollback(self) -> None:
        """Roll back the current database transaction."""
        await self.session.rollback()

    async def __aenter__(self) -> SqlAlchemyUnitOfWork:
        self._session = self._session_factory()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if exc_type is not None:
            await self.rollback()
        if self._session is not None:
            await self._session.close()
            self._session = None
