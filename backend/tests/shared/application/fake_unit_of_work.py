"""Fake UnitOfWork for unit tests."""

from __future__ import annotations

from types import TracebackType

from foundation.application.unit_of_work import UnitOfWork


class FakeUnitOfWork(UnitOfWork):
    """In-memory UoW that tracks commit/rollback calls."""

    def __init__(self) -> None:
        self.committed = False
        self.rolled_back = False

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True

    async def __aenter__(self) -> FakeUnitOfWork:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if exc_type is not None:
            await self.rollback()
