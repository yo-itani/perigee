import pytest

from contexts.workspace.domain.exceptions import InvalidWorkspaceNameError
from contexts.workspace.domain.workspace_name import WorkspaceName


class TestWorkspaceName:
    def test_valid_name(self) -> None:
        name = WorkspaceName("Engineering")
        assert name.value == "Engineering"

    def test_strips_whitespace(self) -> None:
        name = WorkspaceName("  Engineering  ")
        assert name.value == "Engineering"

    def test_empty_raises(self) -> None:
        with pytest.raises(InvalidWorkspaceNameError, match="must not be empty"):
            WorkspaceName("")

    def test_whitespace_only_raises(self) -> None:
        with pytest.raises(InvalidWorkspaceNameError, match="must not be empty"):
            WorkspaceName("   ")

    def test_newline_raises(self) -> None:
        with pytest.raises(
            InvalidWorkspaceNameError, match="must not contain newlines"
        ):
            WorkspaceName("Eng\nTeam")

    def test_carriage_return_raises(self) -> None:
        with pytest.raises(
            InvalidWorkspaceNameError, match="must not contain newlines"
        ):
            WorkspaceName("Eng\rTeam")

    def test_max_length(self) -> None:
        name = WorkspaceName("a" * 100)
        assert len(name.value) == 100

    def test_exceeds_max_length_raises(self) -> None:
        with pytest.raises(InvalidWorkspaceNameError, match="must not exceed 100"):
            WorkspaceName("a" * 101)

    def test_str(self) -> None:
        name = WorkspaceName("Engineering")
        assert str(name) == "Engineering"

    def test_frozen(self) -> None:
        name = WorkspaceName("Engineering")
        with pytest.raises(AttributeError):
            name.value = "Other"  # type: ignore[misc]
