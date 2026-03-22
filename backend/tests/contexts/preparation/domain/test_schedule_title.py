import pytest

from contexts.preparation.domain.exceptions import InvalidScheduleTitleError
from contexts.preparation.domain.schedule_title import ScheduleTitle


class TestScheduleTitle:
    def test_creates_with_valid_value(self) -> None:
        title = ScheduleTitle("Weekly 1on1")
        assert title.value == "Weekly 1on1"

    def test_strips_whitespace(self) -> None:
        title = ScheduleTitle("  padded title  ")
        assert title.value == "padded title"

    def test_empty_raises(self) -> None:
        with pytest.raises(InvalidScheduleTitleError, match="must not be empty"):
            ScheduleTitle("")

    def test_whitespace_only_raises(self) -> None:
        with pytest.raises(InvalidScheduleTitleError, match="must not be empty"):
            ScheduleTitle("   ")

    def test_exceeds_max_length_raises(self) -> None:
        with pytest.raises(InvalidScheduleTitleError, match="must not exceed"):
            ScheduleTitle("a" * 101)

    def test_exactly_max_length_is_valid(self) -> None:
        title = ScheduleTitle("a" * 100)
        assert len(title.value) == 100

    def test_frozen(self) -> None:
        title = ScheduleTitle("title")
        with pytest.raises(AttributeError):
            title.value = "changed"  # type: ignore[misc]

    def test_equality(self) -> None:
        assert ScheduleTitle("title") == ScheduleTitle("title")

    def test_inequality(self) -> None:
        assert ScheduleTitle("title A") != ScheduleTitle("title B")

    def test_str(self) -> None:
        title = ScheduleTitle("My schedule")
        assert str(title) == "My schedule"

    def test_usable_as_dict_key(self) -> None:
        title = ScheduleTitle("title")
        d = {title: "value"}
        assert d[title] == "value"
