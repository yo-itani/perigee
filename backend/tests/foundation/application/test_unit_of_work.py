from abc import ABC

from foundation.application.unit_of_work import UnitOfWork


class TestUnitOfWorkInterface:
    def test_is_abstract(self) -> None:
        assert issubclass(UnitOfWork, ABC)

    def test_abstract_methods(self) -> None:
        assert "commit" in UnitOfWork.__abstractmethods__
        assert "rollback" in UnitOfWork.__abstractmethods__
        assert "__aenter__" in UnitOfWork.__abstractmethods__
        assert "__aexit__" in UnitOfWork.__abstractmethods__
