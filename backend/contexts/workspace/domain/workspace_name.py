from __future__ import annotations

from dataclasses import dataclass

from contexts.workspace.domain.exceptions import InvalidWorkspaceNameError

_WORKSPACE_NAME_MAX_LENGTH = 100


@dataclass(frozen=True)
class WorkspaceName:
    """Value object representing a workspace name.

    Invariants:
    - Must not be empty (after stripping whitespace).
    - Must not contain newlines.
    - Max 100 characters.
    - Leading/trailing whitespace is stripped.
    """

    value: str

    def __init__(self, value: str) -> None:
        stripped = value.strip()
        if not stripped:
            raise InvalidWorkspaceNameError("Workspace name must not be empty.")
        if "\n" in stripped or "\r" in stripped:
            raise InvalidWorkspaceNameError("Workspace name must not contain newlines.")
        if len(stripped) > _WORKSPACE_NAME_MAX_LENGTH:
            raise InvalidWorkspaceNameError(
                f"Workspace name must not exceed"
                f" {_WORKSPACE_NAME_MAX_LENGTH} characters."
            )
        object.__setattr__(self, "value", stripped)

    def __str__(self) -> str:
        return self.value
