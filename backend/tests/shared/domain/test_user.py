"""Domain-level tests for the User entity."""

from shared.domain.user import User
from shared.domain.value_objects import UserId, UserRole


def _make_user(
    role: UserRole = UserRole.MEMBER,
    is_active: bool = True,
    name: str = "Alice",
    email: str = "alice@example.com",
) -> User:
    return User(
        id=UserId.generate(),
        name=name,
        email=email,
        role=role,
        is_active=is_active,
    )


class TestUserProperties:
    def test_default_role_is_member(self) -> None:
        user = User(
            id=UserId.generate(),
            name="Bob",
            email="bob@example.com",
        )
        assert user.role == UserRole.MEMBER

    def test_default_is_active(self) -> None:
        user = User(
            id=UserId.generate(),
            name="Bob",
            email="bob@example.com",
        )
        assert user.is_active is True

    def test_is_admin_true_for_admin_role(self) -> None:
        user = _make_user(role=UserRole.ADMIN)
        assert user.is_admin is True

    def test_is_admin_false_for_member_role(self) -> None:
        user = _make_user(role=UserRole.MEMBER)
        assert user.is_admin is False

    def test_slack_user_id_defaults_to_none(self) -> None:
        user = _make_user()
        assert user.slack_user_id is None

    def test_slack_user_id_can_be_set(self) -> None:
        user = User(
            id=UserId.generate(),
            name="Alice",
            email="alice@example.com",
            slack_user_id="U12345",
        )
        assert user.slack_user_id == "U12345"


class TestUpdateProfile:
    def test_update_name_and_email(self) -> None:
        user = _make_user(name="Alice", email="alice@example.com")
        user.update_profile(name="Alice Smith", email="alice.smith@example.com")
        assert user.name == "Alice Smith"
        assert user.email == "alice.smith@example.com"

    def test_update_does_not_change_role(self) -> None:
        user = _make_user(role=UserRole.ADMIN)
        user.update_profile(name="New Name", email="new@example.com")
        assert user.role == UserRole.ADMIN


class TestActivation:
    def test_deactivate(self) -> None:
        user = _make_user(is_active=True)
        user.deactivate()
        assert user.is_active is False

    def test_activate(self) -> None:
        user = _make_user(is_active=False)
        user.activate()
        assert user.is_active is True


class TestChangeRole:
    def test_change_to_admin(self) -> None:
        user = _make_user(role=UserRole.MEMBER)
        user.change_role(UserRole.ADMIN)
        assert user.role == UserRole.ADMIN

    def test_change_to_member(self) -> None:
        user = _make_user(role=UserRole.ADMIN)
        user.change_role(UserRole.MEMBER)
        assert user.role == UserRole.MEMBER


class TestUserRole:
    def test_admin_value(self) -> None:
        assert UserRole.ADMIN.value == "admin"

    def test_member_value(self) -> None:
        assert UserRole.MEMBER.value == "member"
