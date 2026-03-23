import pytest

from foundation.infrastructure.sqlalchemy_unit_of_work import SqlAlchemyUnitOfWork


class TestSqlAlchemyUnitOfWork:
    def test_session_raises_outside_context(self) -> None:
        """Accessing session outside async with block should raise RuntimeError."""
        # We cannot easily construct a real session_factory without a DB,
        # so we test the guard by passing a dummy factory.
        uow = SqlAlchemyUnitOfWork(None)  # type: ignore[arg-type]
        with pytest.raises(RuntimeError, match="async context manager"):
            _ = uow.session
