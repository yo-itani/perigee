"""Domain exceptions for the workspace context."""


class CircularHierarchyError(Exception):
    """Raised when a workspace hierarchy change would create a circular reference."""

    def __init__(
        self,
        message: str = "Circular hierarchy detected.",
    ) -> None:
        super().__init__(message)


class DuplicateMembershipError(Exception):
    """Raised when attempting to add a user who is already a member."""

    def __init__(
        self,
        message: str = "User is already a member of this workspace.",
    ) -> None:
        super().__init__(message)


class MembershipNotFoundError(Exception):
    """Raised when a membership is not found in the workspace."""

    def __init__(
        self,
        message: str = "Membership not found in this workspace.",
    ) -> None:
        super().__init__(message)


class InvalidWorkspaceNameError(Exception):
    """Raised when a workspace name fails validation."""

    def __init__(self, message: str = "Invalid workspace name.") -> None:
        super().__init__(message)
