"""Time helpers. All datetimes are stored in MongoDB as naive UTC."""
from datetime import datetime, time, timezone
from typing import Optional, Tuple, Union


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def to_naive_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt
    return dt.astimezone(timezone.utc).replace(tzinfo=None)


def as_utc(dt: datetime) -> datetime:
    return dt.replace(tzinfo=timezone.utc)


def parse_time_filter(value: str) -> Tuple[str, Union[datetime, time]]:
    """Parse an ISO datetime ('2026-01-05T22:00:00Z') or a time of day ('22:00:00').

    Returns ("datetime", naive_utc_datetime) or ("time", time_of_day).
    """
    s = (value or "").strip()
    if not s:
        raise ValueError("empty time value")
    try:
        return "datetime", to_naive_utc(datetime.fromisoformat(s))
    except ValueError:
        pass
    try:
        return "time", time.fromisoformat(s).replace(tzinfo=None)
    except ValueError:
        raise ValueError(f"'{value}' is not an ISO datetime or HH:MM[:SS] time of day")


def time_of_day_in_range(t: time, start: Optional[time], end: Optional[time]) -> bool:
    """Inclusive range check; supports ranges that cross midnight (22:00 -> 02:00)."""
    if start is None and end is None:
        return True
    if start is not None and end is not None and start > end:
        return t >= start or t <= end
    if start is not None and t < start:
        return False
    if end is not None and t > end:
        return False
    return True
