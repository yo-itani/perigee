"""Tests for UTC normalization in Record request schemas.

Verifies that non-UTC aware datetimes (e.g. +09:00) are automatically
converted to UTC when parsed by Pydantic request schemas.
"""

from datetime import UTC, datetime, timedelta, timezone

from contexts.record.presentation.schemas import (
    CreatePostHocRecordRequest,
    CreateRecordFromScheduleRequest,
)

JST = timezone(timedelta(hours=9))


class TestCreatePostHocRecordRequestUtcNormalization:
    """UTC normalization for CreatePostHocRecordRequest."""

    def test_jst_offset_normalized_to_utc(self) -> None:
        """A +09:00 conducted_at is converted to equivalent UTC."""
        schema = CreatePostHocRecordRequest(
            counterpart_id="00000000-0000-0000-0000-000000000001",
            conducted_at=datetime(2026, 4, 1, 15, 30, 0, tzinfo=JST),
        )
        assert schema.conducted_at.utcoffset() == timedelta(0)
        expected = datetime(2026, 4, 1, 6, 30, 0, tzinfo=UTC)
        assert schema.conducted_at == expected

    def test_utc_input_unchanged(self) -> None:
        """UTC input passes through without modification."""
        schema = CreatePostHocRecordRequest(
            counterpart_id="00000000-0000-0000-0000-000000000001",
            conducted_at=datetime(2026, 4, 1, 6, 30, 0, tzinfo=UTC),
        )
        assert schema.conducted_at.utcoffset() == timedelta(0)
        expected = datetime(2026, 4, 1, 6, 30, 0, tzinfo=UTC)
        assert schema.conducted_at == expected


class TestCreateRecordFromScheduleRequestUtcNormalization:
    """UTC normalization for CreateRecordFromScheduleRequest."""

    def test_non_utc_offset_normalized(self) -> None:
        """A +09:00 conducted_at is converted to equivalent UTC."""
        schema = CreateRecordFromScheduleRequest(
            schedule_id="00000000-0000-0000-0000-000000000001",
            conducted_at=datetime(2026, 4, 1, 15, 30, 0, tzinfo=JST),
        )
        assert schema.conducted_at.utcoffset() == timedelta(0)
        expected = datetime(2026, 4, 1, 6, 30, 0, tzinfo=UTC)
        assert schema.conducted_at == expected
