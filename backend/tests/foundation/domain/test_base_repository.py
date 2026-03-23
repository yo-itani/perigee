from abc import ABC

import pytest

from foundation.domain.base_repository import BaseRepository


class TestBaseRepositoryInterface:
    def test_is_abstract(self) -> None:
        assert issubclass(BaseRepository, ABC)

    def test_abstract_methods(self) -> None:
        assert "get_by_id" in BaseRepository.__abstractmethods__
        assert "save" in BaseRepository.__abstractmethods__

    def test_cannot_instantiate(self) -> None:
        with pytest.raises(TypeError):
            BaseRepository()  # type: ignore[abstract]
