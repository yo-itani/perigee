from dataclasses import dataclass

from shared.domain.value_objects import UserId


@dataclass
class User:
    """Minimal User entity referenced by all bounded contexts."""

    id: UserId
