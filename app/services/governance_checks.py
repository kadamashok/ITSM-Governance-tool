from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.incident import Incident

MAX_GOVERNANCE_RECORDS = 5000


def generate_governance_report(
    db: Session,
    start_time: datetime,
    period_code: str,
) -> dict[str, Any]:
    incidents = db.execute(
        select(Incident)
        .where(Incident.opened_at >= start_time)
        .order_by(Incident.opened_at.desc())
        .limit(MAX_GOVERNANCE_RECORDS)
    ).scalars().all()
    now = datetime.now(UTC)
    stale_cutoff = now - timedelta(days=3)

    closed_under_two_minutes: list[dict[str, Any]] = []
    missing_resolution_notes: list[dict[str, Any]] = []
    reopened_more_than_two: list[dict[str, Any]] = []
    no_updates_three_plus_days: list[dict[str, Any]] = []

    for incident in incidents:
        opened_at = _to_utc(incident.opened_at)
        resolved_at = _to_utc(incident.resolved_at or incident.closed_at)
        last_updated = _to_utc(incident.updated_at)

        if opened_at and resolved_at:
            resolution_minutes = (resolved_at - opened_at).total_seconds() / 60.0
            if resolution_minutes >= 0 and resolution_minutes < 2:
                closed_under_two_minutes.append(
                    {
                        "number": incident.number,
                        "opened_at": _fmt_dt(opened_at),
                        "resolved_at": _fmt_dt(resolved_at),
                        "resolution_minutes": round(resolution_minutes, 2),
                        "assigned_to": incident.assigned_to,
                        "vendor": incident.vendor,
                    }
                )

        if (incident.resolved_at is not None or incident.closed_at is not None) and not _has_text(
            incident.resolution_notes
        ):
            missing_resolution_notes.append(
                {
                    "number": incident.number,
                    "resolved_at": _fmt_dt(resolved_at),
                    "assigned_to": incident.assigned_to,
                    "vendor": incident.vendor,
                }
            )

        if incident.reopen_count > 2:
            reopened_more_than_two.append(
                {
                    "number": incident.number,
                    "reopen_count": incident.reopen_count,
                    "state": incident.state,
                    "assigned_to": incident.assigned_to,
                    "vendor": incident.vendor,
                }
            )

        is_open = incident.resolved_at is None and incident.closed_at is None
        if is_open and last_updated and last_updated <= stale_cutoff:
            no_updates_three_plus_days.append(
                {
                    "number": incident.number,
                    "last_updated_at": _fmt_dt(last_updated),
                    "days_since_update": round((now - last_updated).total_seconds() / 86400.0, 2),
                    "state": incident.state,
                    "assigned_to": incident.assigned_to,
                    "vendor": incident.vendor,
                }
            )

    total_flagged = (
        len(closed_under_two_minutes)
        + len(missing_resolution_notes)
        + len(reopened_more_than_two)
        + len(no_updates_three_plus_days)
    )

    return {
        "success": True,
        "loading_status": "complete",
        "period": period_code,
        "generated_at": _fmt_dt(now),
        "summary": {
            "total_incidents_scanned": len(incidents),
            "total_flags": total_flagged,
            "closed_under_2_minutes": len(closed_under_two_minutes),
            "without_resolution_notes": len(missing_resolution_notes),
            "reopened_more_than_2_times": len(reopened_more_than_two),
            "without_updates_3_plus_days": len(no_updates_three_plus_days),
        },
        "flags": {
            "closed_under_2_minutes": closed_under_two_minutes,
            "without_resolution_notes": missing_resolution_notes,
            "reopened_more_than_2_times": reopened_more_than_two,
            "without_updates_3_plus_days": no_updates_three_plus_days,
        },
    }


def _has_text(value: str | None) -> bool:
    return bool(value and value.strip())


def _fmt_dt(value: datetime | None) -> str | None:
    if value is None:
        return None
    return _to_utc(value).isoformat()


def _to_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
