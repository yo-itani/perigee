from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

from foundation.infrastructure.sqlalchemy_unit_of_work import SqlAlchemyUnitOfWork


class TestSqlAlchemyUnitOfWork:
    def test_session_property_returns_injected_session(self) -> None:
        """session property should return the AsyncSession passed to __init__."""
        mock_session = MagicMock()
        uow = SqlAlchemyUnitOfWork(mock_session)
        assert uow.session is mock_session

    async def test_aenter_returns_self(self) -> None:
        """__aenter__ should return the UoW itself without calling begin()."""
        mock_session = MagicMock()
        uow = SqlAlchemyUnitOfWork(mock_session)
        result = await uow.__aenter__()
        assert result is uow

    async def test_commit_delegates_to_session(self) -> None:
        """commit() should delegate to session.commit()."""
        mock_session = AsyncMock()
        uow = SqlAlchemyUnitOfWork(mock_session)
        await uow.commit()
        mock_session.commit.assert_awaited_once()

    async def test_rollback_delegates_to_session(self) -> None:
        """rollback() should delegate to session.rollback()."""
        mock_session = AsyncMock()
        uow = SqlAlchemyUnitOfWork(mock_session)
        await uow.rollback()
        mock_session.rollback.assert_awaited_once()

    async def test_aexit_rolls_back_on_exception(self) -> None:
        """__aexit__ should rollback when an exception is raised."""
        mock_session = AsyncMock()
        uow = SqlAlchemyUnitOfWork(mock_session)
        await uow.__aenter__()

        await uow.__aexit__(ValueError, ValueError("test"), None)

        mock_session.rollback.assert_awaited_once()

    async def test_aexit_commits_on_normal_exit(self) -> None:
        """__aexit__ should auto-commit on normal (no exception) exit."""
        mock_session = AsyncMock()
        uow = SqlAlchemyUnitOfWork(mock_session)
        await uow.__aenter__()

        await uow.__aexit__(None, None, None)

        mock_session.commit.assert_awaited_once()
        mock_session.rollback.assert_not_awaited()
