"""Datetime boundary conversion utilities.

All domain-layer datetimes must be timezone-aware UTC.
DB (MariaDB DATETIME(6)) stores naive UTC.

These functions enforce the conversion rules at repository boundaries:
- Domain -> DB: aware UTC -> naive UTC (strip tzinfo)
- DB -> Domain: naive UTC -> aware UTC (attach UTC tzinfo)

Passing a naive datetime where aware is expected (or vice versa) raises
TypeError immediately, preventing silent data corruption.
"""

from datetime import UTC, datetime, timedelta


def normalize_to_utc(dt: datetime) -> datetime:
    """Normalize an aware datetime to UTC.

    Used at the Presentation layer boundary to convert any aware datetime
    (potentially with a non-UTC offset like +09:00) to UTC aware datetime
    before passing it into the domain layer.

    Args:
        dt: A timezone-aware datetime (any offset).

    Returns:
        A timezone-aware datetime in UTC.

    Raises:
        TypeError: If dt is naive (no tzinfo).
    """
    if dt.tzinfo is None:
        raise TypeError(
            f"Expected aware datetime, got naive: {dt!r}. "
            "Use AwareDatetime in Pydantic schemas to ensure awareness."
        )
    return dt.astimezone(UTC)


def to_naive_utc(dt: datetime) -> datetime:
    """Convert an aware UTC datetime to naive UTC for DB storage.

    Args:
        dt: A timezone-aware datetime (must be UTC).

    Returns:
        A naive datetime with the same date/time components.

    Raises:
        TypeError: If dt is naive (no tzinfo).
        ValueError: If dt is not in UTC.
    """
    if dt.tzinfo is None:
        raise TypeError(
            f"Expected aware datetime, got naive: {dt!r}. "
            "Domain datetimes must be timezone-aware UTC."
        )
    if dt.utcoffset() != timedelta(0):
        raise ValueError(
            f"Expected UTC datetime, got offset {dt.utcoffset()}: {dt!r}. "
            "Convert to UTC before storing."
        )
    return dt.replace(tzinfo=None)


def to_aware_utc(dt: datetime) -> datetime:
    """Convert a naive UTC datetime from DB to aware UTC for domain use.

    Args:
        dt: A naive datetime assumed to be in UTC (from DB).

    Returns:
        A timezone-aware datetime with UTC tzinfo.

    Raises:
        TypeError: If dt is already aware (has tzinfo).
    """
    if dt.tzinfo is not None:
        raise TypeError(
            f"Expected naive datetime from DB, got aware: {dt!r}. "
            "DB datetimes should be naive UTC."
        )
    return dt.replace(tzinfo=UTC)


def to_aware_utc_optional(dt: datetime | None) -> datetime | None:
    """Convert an optional naive UTC datetime to aware UTC.

    Returns None if dt is None, otherwise delegates to to_aware_utc.
    """
    if dt is None:
        return None
    return to_aware_utc(dt)
