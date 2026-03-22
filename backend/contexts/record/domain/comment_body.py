from __future__ import annotations

from dataclasses import dataclass

from contexts.record.domain.exceptions import InvalidCommentBodyError

_COMMENT_BODY_MAX_LENGTH = 2000


@dataclass(frozen=True)
class CommentBody:
    """Value object representing a comment body string.

    Invariants:
    - Must not be empty (after stripping whitespace).
    - Max 2000 characters.
    - Leading/trailing whitespace is stripped.
    """

    value: str

    def __init__(self, value: str) -> None:
        stripped = value.strip()
        if not stripped:
            raise InvalidCommentBodyError("Comment body must not be empty.")
        if len(stripped) > _COMMENT_BODY_MAX_LENGTH:
            raise InvalidCommentBodyError(
                f"Comment body must not exceed {_COMMENT_BODY_MAX_LENGTH} characters."
            )
        object.__setattr__(self, "value", stripped)

    def __str__(self) -> str:
        return self.value
