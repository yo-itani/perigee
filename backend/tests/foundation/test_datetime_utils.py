"""Unit tests for foundation.datetime_utils boundary conversion functions."""

from datetime import UTC, datetime, timedelta, timezone

import pytest

from foundation.datetime_utils import (
    normalize_to_utc,
    to_aware_utc,
    to_aware_utc_optional,
    to_naive_utc,
)


class TestNormalizeToUtc:
    """Tests for normalize_to_utc()."""

    def test_utc_datetime_passes_through(self) -> None:
        """UTC aware datetime is returned as-is."""
        utc_dt = datetime(2026, 4, 1, 6, 30, 0, tzinfo=UTC)
        result = normalize_to_utc(utc_dt)

        assert result == utc_dt
        assert result.utcoffset() == timedelta(0)

    def test_positive_offset_converted_to_utc(self) -> None:
        """Datetime with +09:00 offset is converted to equivalent UTC."""
        jst = timezone(timedelta(hours=9))
        jst_dt = datetime(2026, 4, 1, 15, 30, 0, tzinfo=jst)
        result = normalize_to_utc(jst_dt)

        assert result == datetime(2026, 4, 1, 6, 30, 0, tzinfo=UTC)
        assert result.utcoffset() == timedelta(0)

    def test_negative_offset_converted_to_utc(self) -> None:
        """Datetime with -05:00 offset is converted to equivalent UTC."""
        est = timezone(timedelta(hours=-5))
        est_dt = datetime(2026, 4, 1, 1, 30, 0, tzinfo=est)
        result = normalize_to_utc(est_dt)

        assert result == datetime(2026, 4, 1, 6, 30, 0, tzinfo=UTC)
        assert result.utcoffset() == timedelta(0)

    def test_preserves_microseconds(self) -> None:
        """Microsecond precision is preserved during conversion."""
        jst = timezone(timedelta(hours=9))
        jst_dt = datetime(2026, 4, 1, 15, 30, 0, 123456, tzinfo=jst)
        result = normalize_to_utc(jst_dt)

        assert result.microsecond == 123456

    def test_raises_type_error_for_naive_input(self) -> None:
        """Naive datetime input raises TypeError."""
        naive = datetime(2026, 4, 1, 12, 0, 0)
        with pytest.raises(TypeError, match="Expected aware datetime, got naive"):
            normalize_to_utc(naive)


class TestToNaiveUtc:
    """Tests for to_naive_utc()."""

    def test_converts_utc_aware_to_naive(self) -> None:
        """Aware UTC datetime is converted to naive with same components."""
        aware = datetime(2026, 4, 1, 12, 30, 45, 123456, tzinfo=UTC)
        result = to_naive_utc(aware)

        assert result == datetime(2026, 4, 1, 12, 30, 45, 123456)
        assert result.tzinfo is None

    def test_preserves_microseconds(self) -> None:
        """Microsecond precision is preserved through conversion."""
        aware = datetime(2026, 4, 1, 0, 0, 0, 999999, tzinfo=UTC)
        result = to_naive_utc(aware)

        assert result.microsecond == 999999

    def test_raises_type_error_for_naive_input(self) -> None:
        """Naive datetime input raises TypeError."""
        naive = datetime(2026, 4, 1, 12, 0, 0)
        with pytest.raises(TypeError, match="Expected aware datetime, got naive"):
            to_naive_utc(naive)

    def test_raises_value_error_for_non_utc_aware(self) -> None:
        """Aware datetime with non-UTC offset raises ValueError."""
        jst = timezone(timedelta(hours=9))
        aware_jst = datetime(2026, 4, 1, 21, 0, 0, tzinfo=jst)
        with pytest.raises(ValueError, match="Expected UTC datetime"):
            to_naive_utc(aware_jst)


class TestToAwareUtc:
    """Tests for to_aware_utc()."""

    def test_converts_naive_to_utc_aware(self) -> None:
        """Naive datetime is converted to UTC aware with same components."""
        naive = datetime(2026, 4, 1, 6, 30, 0, 0)
        result = to_aware_utc(naive)

        assert result == datetime(2026, 4, 1, 6, 30, 0, 0, tzinfo=UTC)
        assert result.tzinfo is UTC

    def test_preserves_microseconds(self) -> None:
        """Microsecond precision is preserved through conversion."""
        naive = datetime(2026, 4, 1, 0, 0, 0, 123456)
        result = to_aware_utc(naive)

        assert result.microsecond == 123456

    def test_raises_type_error_for_aware_input(self) -> None:
        """Already-aware datetime input raises TypeError."""
        aware = datetime(2026, 4, 1, 12, 0, 0, tzinfo=UTC)
        with pytest.raises(TypeError, match="Expected naive datetime from DB"):
            to_aware_utc(aware)


class TestToAwareUtcOptional:
    """Tests for to_aware_utc_optional()."""

    def test_returns_none_for_none(self) -> None:
        """None input returns None."""
        assert to_aware_utc_optional(None) is None

    def test_converts_naive_to_utc_aware(self) -> None:
        """Non-None naive datetime is converted to UTC aware."""
        naive = datetime(2026, 4, 1, 6, 30, 0, 0)
        result = to_aware_utc_optional(naive)

        assert result is not None
        assert result.tzinfo is UTC
        assert result == datetime(2026, 4, 1, 6, 30, 0, 0, tzinfo=UTC)

    def test_raises_type_error_for_aware_input(self) -> None:
        """Already-aware datetime input raises TypeError."""
        aware = datetime(2026, 4, 1, 12, 0, 0, tzinfo=UTC)
        with pytest.raises(TypeError, match="Expected naive datetime from DB"):
            to_aware_utc_optional(aware)


class TestRoundTrip:
    """Tests for to_naive_utc -> to_aware_utc round-trip."""

    def test_round_trip_preserves_value(self) -> None:
        """Converting aware -> naive -> aware returns the original value."""
        original = datetime(2026, 4, 1, 15, 30, 0, 123456, tzinfo=UTC)
        naive = to_naive_utc(original)
        restored = to_aware_utc(naive)

        assert restored == original
        assert restored.tzinfo is UTC
