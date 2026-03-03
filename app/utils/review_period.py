from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta


ALLOWED_PERIODS: dict[str, timedelta] = {
    "30m": timedelta(minutes=30),
    "1h": timedelta(hours=1),
    "3h": timedelta(hours=3),
    "8h": timedelta(hours=8),
    "1d": timedelta(days=1),
    "5d": timedelta(days=5),
    "10d": timedelta(days=10),
    "15d": timedelta(days=15),
}


@dataclass(frozen=True)
class PeriodRange:
    code: str
    start_time: datetime
    end_time: datetime


def parse_period_range(period: str = "1d") -> PeriodRange:
    code = (period or "1d").strip().lower()
    if code not in ALLOWED_PERIODS:
        allowed = ", ".join(ALLOWED_PERIODS.keys())
        raise ValueError(f"Invalid period '{period}'. Allowed values: {allowed}")

    end_time = datetime.now(UTC)
    start_time = end_time - ALLOWED_PERIODS[code]
    return PeriodRange(code=code, start_time=start_time, end_time=end_time)


def build_servicenow_sysparm_query(start_time: datetime, field: str = "sys_updated_on") -> str:
    normalized = _to_utc(start_time)
    timestamp = normalized.strftime("%Y-%m-%d %H:%M:%S")
    return f"{field}>={timestamp}"


def _to_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
