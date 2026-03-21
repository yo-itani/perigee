from abc import ABC, abstractmethod

from shared.domain.user import User
from shared.domain.value_objects import UserId


class UserRepository(ABC):
    """Interface for user persistence."""

    @abstractmethod
    def get_by_id(self, user_id: UserId) -> User | None: ...

    @abstractmethod
    def exists(self, user_id: UserId) -> bool: ...
