"""Domain exceptions for the notification context."""


class InvalidReminderMinutesError(Exception):
    """Raised when reminder_minutes_before is out of valid range."""

    def __init__(
        self, message: str = "reminder_minutes_before must be between 5 and 1440."
    ) -> None:
        super().__init__(message)


class UnauthorizedOperationError(Exception):
    """Raised when a user attempts to operate on another user's setting."""

    def __init__(self, message: str = "Unauthorized operation.") -> None:
        super().__init__(message)
