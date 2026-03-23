from __future__ import annotations

from abc import ABC, abstractmethod
from types import TracebackType


class UnitOfWork(ABC):
    """Abstract base class for the Unit of Work pattern.

    Designed to be used as an async context manager::

        async with uow:
            repo.save(entity)
            await uow.commit()

    ``commit()`` performs only the database commit.  Event dispatching
    should be done explicitly by the application service after a
    successful commit.
    """

    @abstractmethod
    async def commit(self) -> None:
        """Commit the current transaction."""

    @abstractmethod
    async def rollback(self) -> None:
        """Roll back the current transaction."""

    @abstractmethod
    async def __aenter__(self) -> UnitOfWork:
        """Enter the async context and begin a transaction."""

    @abstractmethod
    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit the async context, rolling back on unhandled exceptions."""
