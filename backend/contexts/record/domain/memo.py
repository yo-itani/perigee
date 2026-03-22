from __future__ import annotations

from dataclasses import dataclass

from contexts.record.domain.exceptions import InvalidMemoError

_MEMO_MAX_LENGTH = 10_000


@dataclass(frozen=True)
class Memo:
    """Value object representing a record memo.

    Invariants:
    - Empty string is allowed.
    - Newlines are allowed.
    - Max 10,000 characters.
    - Leading/trailing whitespace is stripped.
    """

    value: str

    def __init__(self, raw: str) -> None:
        stripped = raw.strip()
        if len(stripped) > _MEMO_MAX_LENGTH:
            raise InvalidMemoError(
                f"Memo must not exceed {_MEMO_MAX_LENGTH} characters."
            )
        object.__setattr__(self, "value", stripped)

    def __str__(self) -> str:
        return self.value
