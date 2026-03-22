from __future__ import annotations

from dataclasses import dataclass

from contexts.preparation.domain.exceptions import InvalidTemplateNameError

_TEMPLATE_NAME_MAX_LENGTH = 100


@dataclass(frozen=True)
class TemplateName:
    """Value object representing a template name string.

    Invariants:
    - Must not be empty (after stripping whitespace).
    - Max 100 characters.
    - Leading/trailing whitespace is stripped.
    """

    value: str

    def __init__(self, value: str) -> None:
        stripped = value.strip()
        if not stripped:
            raise InvalidTemplateNameError("Template name must not be empty.")
        if len(stripped) > _TEMPLATE_NAME_MAX_LENGTH:
            raise InvalidTemplateNameError(
                f"Template name must not exceed {_TEMPLATE_NAME_MAX_LENGTH} characters."
            )
        object.__setattr__(self, "value", stripped)

    def __str__(self) -> str:
        return self.value
