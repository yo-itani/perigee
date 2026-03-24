import pytest

from contexts.record.domain.exceptions import InvalidRetrospectiveBodyError
from contexts.record.domain.retrospective_body import RetrospectiveBody


class TestRetrospectiveBody:
    def test_creates_with_valid_value(self) -> None:
        body = RetrospectiveBody("Good progress on goals.")
        assert body.value == "Good progress on goals."

    def test_strips_whitespace(self) -> None:
        body = RetrospectiveBody("  padded body  ")
        assert body.value == "padded body"

    def test_empty_raises(self) -> None:
        with pytest.raises(InvalidRetrospectiveBodyError, match="must not be empty"):
            RetrospectiveBody("")

    def test_whitespace_only_raises(self) -> None:
        with pytest.raises(InvalidRetrospectiveBodyError, match="must not be empty"):
            RetrospectiveBody("   ")

    def test_exceeds_max_length_raises(self) -> None:
        with pytest.raises(InvalidRetrospectiveBodyError, match="must not exceed"):
            RetrospectiveBody("a" * 2001)

    def test_exactly_max_length_is_valid(self) -> None:
        body = RetrospectiveBody("a" * 2000)
        assert len(body.value) == 2000

    def test_frozen(self) -> None:
        body = RetrospectiveBody("body")
        with pytest.raises(AttributeError):
            body.value = "changed"  # type: ignore[misc]

    def test_equality(self) -> None:
        assert RetrospectiveBody("body") == RetrospectiveBody("body")

    def test_inequality(self) -> None:
        assert RetrospectiveBody("body A") != RetrospectiveBody("body B")

    def test_str(self) -> None:
        body = RetrospectiveBody("My retrospective")
        assert str(body) == "My retrospective"

    def test_usable_as_dict_key(self) -> None:
        body = RetrospectiveBody("body")
        d = {body: "value"}
        assert d[body] == "value"
