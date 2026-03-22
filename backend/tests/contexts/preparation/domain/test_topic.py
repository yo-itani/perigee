import pytest

from contexts.preparation.domain.exceptions import InvalidTopicError
from contexts.preparation.domain.topic import Topic


class TestTopic:
    def test_creates_with_valid_value(self) -> None:
        topic = Topic("Weekly check-in")
        assert topic.value == "Weekly check-in"

    def test_strips_whitespace(self) -> None:
        topic = Topic("  padded topic  ")
        assert topic.value == "padded topic"

    def test_empty_raises(self) -> None:
        with pytest.raises(InvalidTopicError, match="must not be empty"):
            Topic("")

    def test_whitespace_only_raises(self) -> None:
        with pytest.raises(InvalidTopicError, match="must not be empty"):
            Topic("   ")

    def test_newline_raises(self) -> None:
        with pytest.raises(InvalidTopicError, match="must not contain newlines"):
            Topic("line1\nline2")

    def test_carriage_return_raises(self) -> None:
        with pytest.raises(InvalidTopicError, match="must not contain newlines"):
            Topic("line1\rline2")

    def test_exceeds_max_length_raises(self) -> None:
        with pytest.raises(InvalidTopicError, match="must not exceed"):
            Topic("a" * 201)

    def test_exactly_max_length_is_valid(self) -> None:
        topic = Topic("a" * 200)
        assert len(topic.value) == 200

    def test_frozen(self) -> None:
        topic = Topic("topic")
        with pytest.raises(AttributeError):
            topic.value = "changed"  # type: ignore[misc]

    def test_equality(self) -> None:
        assert Topic("topic") == Topic("topic")

    def test_inequality(self) -> None:
        assert Topic("topic A") != Topic("topic B")

    def test_str(self) -> None:
        topic = Topic("My topic")
        assert str(topic) == "My topic"

    def test_usable_as_dict_key(self) -> None:
        topic = Topic("topic")
        d = {topic: "value"}
        assert d[topic] == "value"
