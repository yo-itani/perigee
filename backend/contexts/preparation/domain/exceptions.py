"""Domain exceptions for the preparation context."""


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


class InvalidTopicError(Exception):
    """Raised when a topic value fails validation."""

    def __init__(self, message: str = "Invalid topic.") -> None:
        super().__init__(message)


class InvalidTemplateNameError(Exception):
    """Raised when a template name fails validation."""

    def __init__(self, message: str = "Invalid template name.") -> None:
        super().__init__(message)


class AgendaEditNotAllowedError(Exception):
    """Raised when attempting to edit an agenda topic via ScheduleGroup."""

    def __init__(
        self,
        message: str = "Editing agenda topics via ScheduleGroup is not allowed. "
        "Delete and re-add instead.",
    ) -> None:
        super().__init__(message)


class InconsistentScheduleAgendasError(Exception):
    """Raised when schedules_agendas dict is missing keys
    for registered schedule IDs."""

    def __init__(
        self,
        message: str = "schedules_agendas is missing registered schedule IDs.",
    ) -> None:
        super().__init__(message)


class UnauthorizedScheduleGroupOperationError(Exception):
    """Raised when a user without permission attempts a ScheduleGroup operation."""

    def __init__(self, message: str = "Unauthorized schedule group operation.") -> None:
        super().__init__(message)


class UnauthorizedTemplateOperationError(Exception):
    """Raised when a user without permission attempts a Template operation."""

    def __init__(self, message: str = "Unauthorized template operation.") -> None:
        super().__init__(message)


class InvalidScheduleTitleError(Exception):
    """Raised when a schedule title fails validation."""

    def __init__(self, message: str = "Invalid schedule title.") -> None:
        super().__init__(message)


class InvalidCommentBodyError(Exception):
    """Raised when a comment body fails validation."""

    def __init__(self, message: str = "Invalid comment body.") -> None:
        super().__init__(message)
