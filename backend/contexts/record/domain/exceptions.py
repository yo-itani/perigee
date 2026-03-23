"""Domain exceptions for the recording context."""


class RecordAlreadyPublishedError(Exception):
    """Raised when attempting to edit or re-publish a published record."""

    def __init__(self, message: str = "Record is already published.") -> None:
        super().__init__(message)


class UnauthorizedOperationError(Exception):
    """Raised when a user without permission attempts an operation."""

    def __init__(self, message: str = "Unauthorized operation.") -> None:
        super().__init__(message)


class ActionItemAlreadyCompletedError(Exception):
    """Raised when attempting to complete an already-completed action item."""

    def __init__(self, message: str = "Action item is already completed.") -> None:
        super().__init__(message)


class InvalidActionItemTitleError(Exception):
    """Raised when an action item title fails validation."""

    def __init__(self, message: str = "Invalid action item title.") -> None:
        super().__init__(message)


class InvalidCommentBodyError(Exception):
    """Raised when a comment body fails validation."""

    def __init__(self, message: str = "Invalid comment body.") -> None:
        super().__init__(message)


class CommentAlreadyExistsError(Exception):
    """Raised when attempting to save a comment that already exists."""

    def __init__(self, message: str = "Comment already exists.") -> None:
        super().__init__(message)


class InvalidMemoError(Exception):
    """Raised when a memo fails validation."""

    def __init__(self, message: str = "Invalid memo.") -> None:
        super().__init__(message)
