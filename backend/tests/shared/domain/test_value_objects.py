import uuid

from shared.domain.value_objects import UserId


class TestUserId:
    def test_generate_creates_unique_ids(self) -> None:
        id1 = UserId.generate()
        id2 = UserId.generate()
        assert id1 != id2

    def test_from_str_roundtrip(self) -> None:
        raw = "550e8400-e29b-41d4-a716-446655440000"
        user_id = UserId.from_str(raw)
        assert str(user_id.value) == raw

    def test_equality_same_uuid(self) -> None:
        raw = uuid.UUID("550e8400-e29b-41d4-a716-446655440000")
        assert UserId(value=raw) == UserId(value=raw)

    def test_inequality_different_uuid(self) -> None:
        id1 = UserId.generate()
        id2 = UserId.generate()
        assert id1 != id2

    def test_frozen(self) -> None:
        user_id = UserId.generate()
        try:
            user_id.value = uuid.uuid4()  # type: ignore[misc]
            raise AssertionError("Expected FrozenInstanceError")  # noqa: TRY301
        except AttributeError:
            pass

    def test_usable_as_dict_key(self) -> None:
        user_id = UserId.generate()
        d = {user_id: "alice"}
        assert d[user_id] == "alice"
