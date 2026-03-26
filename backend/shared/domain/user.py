from __future__ import annotations

from shared.domain.value_objects import UserId, UserRole


class User:
    """User entity referenced by all bounded contexts."""

    def __init__(
        self,
        id: UserId,
        name: str,
        email: str,
        role: UserRole = UserRole.MEMBER,
        is_active: bool = True,
        slack_user_id: str | None = None,
    ) -> None:
        self._id = id
        self._name = name
        self._email = email
        self._role = role
        self._is_active = is_active
        self._slack_user_id = slack_user_id

    @property
    def id(self) -> UserId:
        return self._id

    @property
    def name(self) -> str:
        return self._name

    @property
    def email(self) -> str:
        return self._email

    @property
    def role(self) -> UserRole:
        return self._role

    @property
    def is_active(self) -> bool:
        return self._is_active

    @property
    def slack_user_id(self) -> str | None:
        return self._slack_user_id

    @property
    def is_admin(self) -> bool:
        return self._role == UserRole.ADMIN

    def update_profile(self, name: str, email: str) -> None:
        """Update user profile (name and email only, not role)."""
        self._name = name
        self._email = email

    def deactivate(self) -> None:
        self._is_active = False

    def activate(self) -> None:
        self._is_active = True

    def change_role(self, new_role: UserRole) -> None:
        self._role = new_role
