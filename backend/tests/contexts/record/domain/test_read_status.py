from datetime import UTC, datetime

from contexts.record.domain.read_status import ReadStatus
from contexts.record.domain.value_objects import ReadStatusId, RecordId
from shared.domain.value_objects import UserId


class TestCreate:
    """ReadStatus.create() factory method."""

    def test_create_sets_fields(self) -> None:
        record_id = RecordId.generate()
        user_id = UserId.generate()
        now = datetime(2026, 3, 20, 10, 0, tzinfo=UTC)

        rs = ReadStatus.create(record_id=record_id, user_id=user_id, now=now)

        assert rs.record_id == record_id
        assert rs.user_id == user_id
        assert rs.last_viewed_at == now
        assert isinstance(rs.id, ReadStatusId)

    def test_create_generates_unique_ids(self) -> None:
        record_id = RecordId.generate()
        user_id = UserId.generate()

        rs1 = ReadStatus.create(record_id=record_id, user_id=user_id)
        rs2 = ReadStatus.create(record_id=record_id, user_id=user_id)

        assert rs1.id != rs2.id

    def test_create_defaults_to_utc_now(self) -> None:
        before = datetime.now(UTC)
        rs = ReadStatus.create(
            record_id=RecordId.generate(),
            user_id=UserId.generate(),
        )
        after = datetime.now(UTC)

        assert before <= rs.last_viewed_at <= after


class TestMarkViewed:
    """ReadStatus.mark_viewed() updates last_viewed_at."""

    def test_mark_viewed_updates_timestamp(self) -> None:
        initial_time = datetime(2026, 3, 20, 10, 0, tzinfo=UTC)
        new_time = datetime(2026, 3, 20, 15, 0, tzinfo=UTC)

        rs = ReadStatus.create(
            record_id=RecordId.generate(),
            user_id=UserId.generate(),
            now=initial_time,
        )
        assert rs.last_viewed_at == initial_time

        rs.mark_viewed(now=new_time)

        assert rs.last_viewed_at == new_time

    def test_mark_viewed_can_be_called_multiple_times(self) -> None:
        rs = ReadStatus.create(
            record_id=RecordId.generate(),
            user_id=UserId.generate(),
            now=datetime(2026, 3, 20, 10, 0, tzinfo=UTC),
        )

        second = datetime(2026, 3, 20, 12, 0, tzinfo=UTC)
        third = datetime(2026, 3, 20, 14, 0, tzinfo=UTC)

        rs.mark_viewed(now=second)
        assert rs.last_viewed_at == second

        rs.mark_viewed(now=third)
        assert rs.last_viewed_at == third
