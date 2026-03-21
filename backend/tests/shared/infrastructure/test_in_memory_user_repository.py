from shared.domain.user import User
from shared.domain.value_objects import UserId
from shared.infrastructure.in_memory_user_repository import InMemoryUserRepository


class TestInMemoryUserRepository:
    def test_get_by_id_returns_user(self) -> None:
        user = User(id=UserId.generate())
        repo = InMemoryUserRepository(users=[user])

        result = repo.get_by_id(user.id)

        assert result is not None
        assert result.id == user.id

    def test_get_by_id_returns_none_for_unknown(self) -> None:
        repo = InMemoryUserRepository()

        result = repo.get_by_id(UserId.generate())

        assert result is None

    def test_exists_returns_true(self) -> None:
        user = User(id=UserId.generate())
        repo = InMemoryUserRepository(users=[user])

        assert repo.exists(user.id) is True

    def test_exists_returns_false(self) -> None:
        repo = InMemoryUserRepository()

        assert repo.exists(UserId.generate()) is False

    def test_add_then_get(self) -> None:
        repo = InMemoryUserRepository()
        user = User(id=UserId.generate())

        repo.add(user)

        assert repo.get_by_id(user.id) == user

    def test_init_with_multiple_users(self) -> None:
        users = [User(id=UserId.generate()) for _ in range(3)]
        repo = InMemoryUserRepository(users=users)

        for user in users:
            assert repo.exists(user.id) is True
