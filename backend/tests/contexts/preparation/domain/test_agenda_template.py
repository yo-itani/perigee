import pytest

from contexts.preparation.domain.agenda_template import AgendaTemplate
from contexts.preparation.domain.exceptions import InvalidAgendaTopicError


class TestAgendaTemplate:
    def test_creates_with_valid_topic(self) -> None:
        tmpl = AgendaTemplate("Weekly check-in")
        assert tmpl.topic == "Weekly check-in"

    def test_strips_whitespace(self) -> None:
        tmpl = AgendaTemplate("  padded topic  ")
        assert tmpl.topic == "padded topic"

    def test_empty_topic_raises(self) -> None:
        with pytest.raises(InvalidAgendaTopicError, match="must not be empty"):
            AgendaTemplate("")

    def test_whitespace_only_raises(self) -> None:
        with pytest.raises(InvalidAgendaTopicError, match="must not be empty"):
            AgendaTemplate("   ")

    def test_newline_raises(self) -> None:
        with pytest.raises(InvalidAgendaTopicError, match="must not contain newlines"):
            AgendaTemplate("line1\nline2")

    def test_carriage_return_raises(self) -> None:
        with pytest.raises(InvalidAgendaTopicError, match="must not contain newlines"):
            AgendaTemplate("line1\rline2")

    def test_exceeds_max_length_raises(self) -> None:
        with pytest.raises(InvalidAgendaTopicError, match="must not exceed"):
            AgendaTemplate("a" * 201)

    def test_exactly_max_length_is_valid(self) -> None:
        tmpl = AgendaTemplate("a" * 200)
        assert len(tmpl.topic) == 200

    def test_frozen(self) -> None:
        tmpl = AgendaTemplate("topic")
        with pytest.raises(AttributeError):
            tmpl.topic = "changed"  # type: ignore[misc]

    def test_equality(self) -> None:
        assert AgendaTemplate("topic") == AgendaTemplate("topic")

    def test_inequality(self) -> None:
        assert AgendaTemplate("topic A") != AgendaTemplate("topic B")

    def test_str(self) -> None:
        tmpl = AgendaTemplate("My topic")
        assert str(tmpl) == "My topic"

    def test_usable_as_dict_key(self) -> None:
        tmpl = AgendaTemplate("topic")
        d = {tmpl: "value"}
        assert d[tmpl] == "value"
