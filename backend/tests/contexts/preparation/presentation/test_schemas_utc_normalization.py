"""Tests for UTC normalization in Preparation request schemas.

Verifies that non-UTC aware datetimes (e.g. +09:00) are automatically
converted to UTC when parsed by Pydantic request schemas.
"""

from datetime import UTC, datetime, timedelta, timezone

from contexts.preparation.presentation.schemas import (
    CounterpartScheduleSchema,
    CreateScheduleRequest,
    RescheduleRequest,
    SendConsultationRequestRequest,
)

JST = timezone(timedelta(hours=9))
EST = timezone(timedelta(hours=-5))


class TestCounterpartScheduleSchemaUtcNormalization:
    """UTC normalization for CounterpartScheduleSchema."""

    def test_jst_offset_normalized_to_utc(self) -> None:
        """A +09:00 scheduled_at is converted to equivalent UTC."""
        schema = CounterpartScheduleSchema(
            counterpart_id="00000000-0000-0000-0000-000000000001",
            scheduled_at=datetime(2026, 4, 1, 15, 30, 0, tzinfo=JST),
        )
        assert schema.scheduled_at.utcoffset() == timedelta(0)
        expected = datetime(2026, 4, 1, 6, 30, 0, tzinfo=UTC)
        assert schema.scheduled_at == expected

    def test_utc_input_unchanged(self) -> None:
        """UTC input passes through without modification."""
        schema = CounterpartScheduleSchema(
            counterpart_id="00000000-0000-0000-0000-000000000001",
            scheduled_at=datetime(2026, 4, 1, 6, 30, 0, tzinfo=UTC),
        )
        assert schema.scheduled_at.utcoffset() == timedelta(0)
        expected = datetime(2026, 4, 1, 6, 30, 0, tzinfo=UTC)
        assert schema.scheduled_at == expected


class TestCreateScheduleRequestUtcNormalization:
    """UTC normalization for CreateScheduleRequest."""

    def test_non_utc_offset_normalized(self) -> None:
        """A -05:00 scheduled_at is converted to equivalent UTC."""
        schema = CreateScheduleRequest(
            counterpart_id="00000000-0000-0000-0000-000000000001",
            scheduled_at=datetime(2026, 4, 1, 1, 30, 0, tzinfo=EST),
            title="Test",
        )
        assert schema.scheduled_at.utcoffset() == timedelta(0)
        expected = datetime(2026, 4, 1, 6, 30, 0, tzinfo=UTC)
        assert schema.scheduled_at == expected


class TestSendConsultationRequestRequestUtcNormalization:
    """UTC normalization for SendConsultationRequestRequest."""

    def test_non_utc_offset_normalized(self) -> None:
        """A +09:00 scheduled_at is converted to equivalent UTC."""
        schema = SendConsultationRequestRequest(
            organizer_id="00000000-0000-0000-0000-000000000001",
            scheduled_at=datetime(2026, 4, 1, 15, 30, 0, tzinfo=JST),
            title="Test",
            agenda_topics=["Topic 1"],
        )
        assert schema.scheduled_at.utcoffset() == timedelta(0)
        expected = datetime(2026, 4, 1, 6, 30, 0, tzinfo=UTC)
        assert schema.scheduled_at == expected


class TestRescheduleRequestUtcNormalization:
    """UTC normalization for RescheduleRequest."""

    def test_non_utc_offset_normalized(self) -> None:
        """A +09:00 new_scheduled_at is converted to UTC."""
        schema = RescheduleRequest(
            new_scheduled_at=datetime(2026, 4, 1, 15, 30, 0, tzinfo=JST),
        )
        assert schema.new_scheduled_at.utcoffset() == timedelta(0)
        expected = datetime(2026, 4, 1, 6, 30, 0, tzinfo=UTC)
        assert schema.new_scheduled_at == expected
