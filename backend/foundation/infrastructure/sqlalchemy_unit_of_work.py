from __future__ import annotations

from types import TracebackType

from sqlalchemy.ext.asyncio import AsyncSession

from foundation.application.unit_of_work import UnitOfWork


class SqlAlchemyUnitOfWork(UnitOfWork):
    """Unit of Work implementation backed by a SQLAlchemy ``AsyncSession``.

    Receives an ``AsyncSession`` directly (typically injected via FastAPI
    ``Depends``), so that repositories and the UoW share the same session.

    Usage::

        uow = SqlAlchemyUnitOfWork(session)
        async with uow:
            # repositories use the same session
        # auto-commit here

    The UoW relies on SQLAlchemy's *autobegin* behaviour -- ``__aenter__``
    does **not** call ``begin()`` explicitly.  On normal exit the
    transaction is committed automatically.  On exception exit, any
    uncommitted changes are rolled back.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @property
    def session(self) -> AsyncSession:
        """Return the underlying session."""
        return self._session

    async def commit(self) -> None:
        """Commit the current database transaction."""
        await self._session.commit()

    async def rollback(self) -> None:
        """Roll back the current database transaction."""
        await self._session.rollback()

    async def __aenter__(self) -> SqlAlchemyUnitOfWork:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if exc_type is not None:
            await self.rollback()
        else:
            await self.commit()
