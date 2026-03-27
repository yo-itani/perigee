from shared.domain.user import User
from shared.domain.user_repository import UserRepository
from shared.domain.value_objects import UserId, UserRole


class InMemoryUserRepository(UserRepository):
    """Stub implementation backed by a fixed set of users."""

    def __init__(self, users: list[User] | None = None) -> None:
        self._users: dict[UserId, User] = {u.id: u for u in (users or [])}

    # -- mutation helpers (not part of the interface) -------------------------

    def add(self, user: User) -> None:
        self._users[user.id] = user

    # -- UserRepository interface --------------------------------------------

    async def get_by_id(self, user_id: UserId) -> User | None:
        return self._users.get(user_id)

    async def get_by_email(self, email: str) -> User | None:
        for user in self._users.values():
            if user.email == email:
                return user
        return None

    async def exists(self, user_id: UserId) -> bool:
        return user_id in self._users

    async def save(self, user: User) -> None:
        self._users[user.id] = user

    async def list_all(self, *, offset: int = 0, limit: int = 100) -> list[User]:
        all_users = sorted(self._users.values(), key=lambda u: u.name)
        return all_users[offset : offset + limit]

    async def count_active_admins(self) -> int:
        return sum(
            1 for u in self._users.values() if u.role == UserRole.ADMIN and u.is_active
        )
