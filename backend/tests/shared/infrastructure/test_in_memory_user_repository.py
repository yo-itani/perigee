import pytest

from shared.domain.user import User
from shared.domain.value_objects import UserId, UserRole
from shared.infrastructure.in_memory_user_repository import InMemoryUserRepository


def _make_user(
    user_id: UserId | None = None,
    name: str = "Test User",
    email: str | None = None,
    role: UserRole = UserRole.MEMBER,
) -> User:
    uid = user_id or UserId.generate()
    return User(
        id=uid,
        name=name,
        email=email or f"{uid.value}@test.local",
        role=role,
    )


class TestInMemoryUserRepository:
    @pytest.mark.asyncio
    async def test_get_by_id_returns_user(self) -> None:
        user = _make_user()
        repo = InMemoryUserRepository(users=[user])

        result = await repo.get_by_id(user.id)

        assert result is not None
        assert result.id == user.id

    @pytest.mark.asyncio
    async def test_get_by_id_returns_none_for_unknown(self) -> None:
        repo = InMemoryUserRepository()

        result = await repo.get_by_id(UserId.generate())

        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_email(self) -> None:
        user = _make_user(email="alice@example.com")
        repo = InMemoryUserRepository(users=[user])

        result = await repo.get_by_email("alice@example.com")
        assert result is not None
        assert result.id == user.id

    @pytest.mark.asyncio
    async def test_get_by_email_returns_none(self) -> None:
        repo = InMemoryUserRepository()
        result = await repo.get_by_email("nobody@example.com")
        assert result is None

    @pytest.mark.asyncio
    async def test_exists_returns_true(self) -> None:
        user = _make_user()
        repo = InMemoryUserRepository(users=[user])

        assert await repo.exists(user.id) is True

    @pytest.mark.asyncio
    async def test_exists_returns_false(self) -> None:
        repo = InMemoryUserRepository()

        assert await repo.exists(UserId.generate()) is False

    @pytest.mark.asyncio
    async def test_add_then_get(self) -> None:
        repo = InMemoryUserRepository()
        user = _make_user()

        repo.add(user)

        result = await repo.get_by_id(user.id)
        assert result is not None
        assert result.id == user.id

    @pytest.mark.asyncio
    async def test_save(self) -> None:
        repo = InMemoryUserRepository()
        user = _make_user()

        await repo.save(user)

        result = await repo.get_by_id(user.id)
        assert result is not None
        assert result.id == user.id

    @pytest.mark.asyncio
    async def test_init_with_multiple_users(self) -> None:
        users = [_make_user() for _ in range(3)]
        repo = InMemoryUserRepository(users=users)

        for user in users:
            assert await repo.exists(user.id) is True
