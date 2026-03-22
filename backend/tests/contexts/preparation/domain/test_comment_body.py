import pytest

from contexts.preparation.domain.comment_body import CommentBody
from contexts.preparation.domain.exceptions import InvalidCommentBodyError


class TestCommentBody:
    def test_creates_with_valid_value(self) -> None:
        body = CommentBody("Hello, world!")
        assert body.value == "Hello, world!"

    def test_strips_whitespace(self) -> None:
        body = CommentBody("  padded body  ")
        assert body.value == "padded body"

    def test_empty_raises(self) -> None:
        with pytest.raises(InvalidCommentBodyError, match="must not be empty"):
            CommentBody("")

    def test_whitespace_only_raises(self) -> None:
        with pytest.raises(InvalidCommentBodyError, match="must not be empty"):
            CommentBody("   ")

    def test_exceeds_max_length_raises(self) -> None:
        with pytest.raises(InvalidCommentBodyError, match="must not exceed"):
            CommentBody("a" * 2001)

    def test_exactly_max_length_is_valid(self) -> None:
        body = CommentBody("a" * 2000)
        assert len(body.value) == 2000

    def test_frozen(self) -> None:
        body = CommentBody("body")
        with pytest.raises(AttributeError):
            body.value = "changed"  # type: ignore[misc]

    def test_equality(self) -> None:
        assert CommentBody("body") == CommentBody("body")

    def test_inequality(self) -> None:
        assert CommentBody("body A") != CommentBody("body B")

    def test_str(self) -> None:
        body = CommentBody("My body")
        assert str(body) == "My body"

    def test_usable_as_dict_key(self) -> None:
        body = CommentBody("body")
        d = {body: "value"}
        assert d[body] == "value"
