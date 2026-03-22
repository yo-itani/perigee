import uuid

import pytest

from contexts.workspace.domain.value_objects import (
    MembershipId,
    MembershipRole,
    WorkspaceId,
)


class TestWorkspaceId:
    def test_generate(self) -> None:
        wid = WorkspaceId.generate()
        assert isinstance(wid.value, uuid.UUID)

    def test_from_str(self) -> None:
        raw = "12345678-1234-5678-1234-567812345678"
        wid = WorkspaceId.from_str(raw)
        assert str(wid.value) == raw

    def test_from_str_invalid_raises(self) -> None:
        with pytest.raises(ValueError):
            WorkspaceId.from_str("not-a-uuid")

    def test_equality(self) -> None:
        raw = "12345678-1234-5678-1234-567812345678"
        assert WorkspaceId.from_str(raw) == WorkspaceId.from_str(raw)

    def test_inequality(self) -> None:
        assert WorkspaceId.generate() != WorkspaceId.generate()


class TestMembershipId:
    def test_generate(self) -> None:
        mid = MembershipId.generate()
        assert isinstance(mid.value, uuid.UUID)

    def test_from_str(self) -> None:
        raw = "12345678-1234-5678-1234-567812345678"
        mid = MembershipId.from_str(raw)
        assert str(mid.value) == raw


class TestMembershipRole:
    def test_captain(self) -> None:
        assert MembershipRole.CAPTAIN.value == "captain"

    def test_member(self) -> None:
        assert MembershipRole.MEMBER.value == "member"
