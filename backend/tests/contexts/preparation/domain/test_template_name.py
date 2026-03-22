import pytest

from contexts.preparation.domain.exceptions import InvalidTemplateNameError
from contexts.preparation.domain.template_name import TemplateName


class TestTemplateName:
    def test_creates_with_valid_value(self) -> None:
        name = TemplateName("Monthly 1on1")
        assert name.value == "Monthly 1on1"

    def test_strips_whitespace(self) -> None:
        name = TemplateName("  padded name  ")
        assert name.value == "padded name"

    def test_empty_raises(self) -> None:
        with pytest.raises(InvalidTemplateNameError, match="must not be empty"):
            TemplateName("")

    def test_whitespace_only_raises(self) -> None:
        with pytest.raises(InvalidTemplateNameError, match="must not be empty"):
            TemplateName("   ")

    def test_exceeds_max_length_raises(self) -> None:
        with pytest.raises(InvalidTemplateNameError, match="must not exceed"):
            TemplateName("a" * 101)

    def test_exactly_max_length_is_valid(self) -> None:
        name = TemplateName("a" * 100)
        assert len(name.value) == 100

    def test_frozen(self) -> None:
        name = TemplateName("name")
        with pytest.raises(AttributeError):
            name.value = "changed"  # type: ignore[misc]

    def test_equality(self) -> None:
        assert TemplateName("name") == TemplateName("name")

    def test_inequality(self) -> None:
        assert TemplateName("name A") != TemplateName("name B")

    def test_str(self) -> None:
        name = TemplateName("My template")
        assert str(name) == "My template"

    def test_usable_as_dict_key(self) -> None:
        name = TemplateName("name")
        d = {name: "value"}
        assert d[name] == "value"
