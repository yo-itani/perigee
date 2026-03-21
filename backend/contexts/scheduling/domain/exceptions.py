"""Domain exceptions for the scheduling context."""


class ScheduleAlreadyCancelledError(Exception):
    """Raised when attempting to operate on a cancelled schedule."""

    def __init__(self, message: str = "Schedule is already cancelled.") -> None:
        super().__init__(message)


class UnauthorizedScheduleOperationError(Exception):
    """Raised when a user without permission attempts a schedule operation."""

    def __init__(self, message: str = "Unauthorized schedule operation.") -> None:
        super().__init__(message)


class InvalidScheduleOperationError(Exception):
    """Raised when a schedule operation is invalid."""

    def __init__(self, message: str = "Invalid schedule operation.") -> None:
        super().__init__(message)


class NoPendingConfirmationRequestError(Exception):
    """Raised when confirm/reject is attempted without a pending request."""

    def __init__(self, message: str = "No pending confirmation request.") -> None:
        super().__init__(message)
