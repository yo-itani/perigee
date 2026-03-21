import uuid

from contexts.preparation.domain.value_objects import ScheduleId


class TestScheduleId:
    def test_generate_creates_unique_ids(self) -> None:
        id1 = ScheduleId.generate()
        id2 = ScheduleId.generate()
        assert id1 != id2

    def test_from_str_roundtrip(self) -> None:
        raw = "550e8400-e29b-41d4-a716-446655440000"
        schedule_id = ScheduleId.from_str(raw)
        assert str(schedule_id.value) == raw

    def test_equality_same_uuid(self) -> None:
        raw = uuid.UUID("550e8400-e29b-41d4-a716-446655440000")
        assert ScheduleId(value=raw) == ScheduleId(value=raw)

    def test_inequality_different_uuid(self) -> None:
        id1 = ScheduleId.generate()
        id2 = ScheduleId.generate()
        assert id1 != id2

    def test_frozen(self) -> None:
        schedule_id = ScheduleId.generate()
        try:
            schedule_id.value = uuid.uuid4()  # type: ignore[misc]
            raise AssertionError("Expected FrozenInstanceError")  # noqa: TRY301
        except AttributeError:
            pass

    def test_usable_as_dict_key(self) -> None:
        schedule_id = ScheduleId.generate()
        d = {schedule_id: "meeting"}
        assert d[schedule_id] == "meeting"
