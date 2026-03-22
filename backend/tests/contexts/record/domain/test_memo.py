import pytest

from contexts.record.domain.exceptions import InvalidMemoError
from contexts.record.domain.memo import Memo


class TestMemo:
    def test_empty_string_is_allowed(self) -> None:
        memo = Memo("")
        assert memo.value == ""

    def test_strips_whitespace(self) -> None:
        memo = Memo("  hello  ")
        assert memo.value == "hello"

    def test_whitespace_only_becomes_empty(self) -> None:
        memo = Memo("   ")
        assert memo.value == ""

    def test_newlines_are_allowed(self) -> None:
        memo = Memo("line1\nline2\nline3")
        assert memo.value == "line1\nline2\nline3"

    def test_max_length_is_valid(self) -> None:
        memo = Memo("a" * 10_000)
        assert len(memo.value) == 10_000

    def test_exceeds_max_length_raises(self) -> None:
        with pytest.raises(InvalidMemoError, match="must not exceed"):
            Memo("a" * 10_001)

    def test_str_returns_value(self) -> None:
        memo = Memo("some memo")
        assert str(memo) == "some memo"

    def test_equality(self) -> None:
        assert Memo("hello") == Memo("hello")

    def test_frozen(self) -> None:
        memo = Memo("hello")
        with pytest.raises(AttributeError):
            memo.value = "changed"  # type: ignore[misc]
