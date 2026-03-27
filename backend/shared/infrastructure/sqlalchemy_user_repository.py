from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.domain.user import User
from shared.domain.user_repository import UserRepository
from shared.domain.value_objects import UserId, UserRole
from shared.infrastructure.tables import UserTable


class SqlAlchemyUserRepository(UserRepository):
    """SQLAlchemy-based implementation of UserRepository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, user_id: UserId) -> User | None:
        row = await self._session.get(UserTable, str(user_id.value))
        if row is None:
            return None
        return self._to_entity(row)

    async def get_by_email(self, email: str) -> User | None:
        stmt = select(UserTable).where(UserTable.email == email)
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        if row is None:
            return None
        return self._to_entity(row)

    async def exists(self, user_id: UserId) -> bool:
        row = await self._session.get(UserTable, str(user_id.value))
        return row is not None

    async def save(self, user: User) -> None:
        existing = await self._session.get(UserTable, str(user.id.value))
        if existing is None:
            await self._insert(user)
        else:
            self._update(user, existing)
            await self._session.flush()

    async def _insert(self, user: User) -> None:
        row = UserTable(
            id=str(user.id.value),
            name=user.name,
            email=user.email,
            role=user.role.value,
            is_active=user.is_active,
            slack_user_id=user.slack_user_id,
        )
        self._session.add(row)
        await self._session.flush()

    @staticmethod
    def _update(user: User, existing: UserTable) -> None:
        existing.name = user.name
        existing.email = user.email
        existing.role = user.role.value
        existing.is_active = user.is_active
        existing.slack_user_id = user.slack_user_id

    async def list_all(self, *, offset: int = 0, limit: int = 100) -> list[User]:
        stmt = select(UserTable).order_by(UserTable.name).offset(offset).limit(limit)
        result = await self._session.execute(stmt)
        rows = result.scalars().all()
        return [self._to_entity(row) for row in rows]

    async def count_all(self) -> int:
        stmt = select(func.count()).select_from(UserTable)
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def count_active_admins(self) -> int:
        stmt = (
            select(func.count())
            .select_from(UserTable)
            .where(
                UserTable.role == UserRole.ADMIN.value,
                UserTable.is_active.is_(True),
            )
            .with_for_update()
        )
        result = await self._session.execute(stmt)
        return result.scalar_one()

    @staticmethod
    def _to_entity(row: UserTable) -> User:
        return User(
            id=UserId.from_str(row.id),
            name=row.name,
            email=row.email,
            role=UserRole(row.role),
            is_active=row.is_active,
            slack_user_id=row.slack_user_id,
        )
