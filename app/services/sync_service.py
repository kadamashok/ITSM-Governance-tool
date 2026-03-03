from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.incident import Incident
from app.services.servicenow_client import ServiceNowClient, ServiceNowClientError
from app.utils.config import Settings

logger = logging.getLogger(__name__)


def build_servicenow_client(settings: Settings) -> ServiceNowClient:
    if settings.servicenow_instance_url:
        return ServiceNowClient(
            instance_url=settings.servicenow_instance_url,
            timeout_seconds=settings.servicenow_timeout_seconds,
            page_size=settings.servicenow_page_size,
        )
    return ServiceNowClient(
        timeout_seconds=settings.servicenow_timeout_seconds,
        page_size=settings.servicenow_page_size,
    )


def run_incident_sync(
    db: Session,
    client: ServiceNowClient,
    start_time: datetime | None = None,
    max_records: int = 500,
) -> dict[str, Any]:
    try:
        remote_payload = client.fetch_incidents(start_time=start_time, max_records=max_records)
    except ServiceNowClientError:
        logger.exception("Incident sync failed while fetching ServiceNow incidents")
        raise

    raw_records = remote_payload.get("data", [])
    if not isinstance(raw_records, list):
        raise ValueError("Invalid ServiceNow response. Expected list in 'data'.")

    transformed_records: list[dict[str, Any]] = []
    failed = 0

    for record in raw_records:
        try:
            transformed = _transform_incident(record)
            if not transformed["number"]:
                failed += 1
                logger.error("Skipping incident without number: %s", record)
                continue
            transformed_records.append(transformed)
        except Exception:
            failed += 1
            logger.exception("Failed transforming incident record")

    incident_numbers = [row["number"] for row in transformed_records]
    existing_by_number: dict[str, Incident] = {}
    if incident_numbers:
        query = select(Incident).where(Incident.number.in_(incident_numbers))
        existing_rows = db.execute(query).scalars().all()
        existing_by_number = {row.number: row for row in existing_rows}

    inserted = 0
    updated = 0

    for payload in transformed_records:
        number = payload["number"]
        try:
            with db.begin_nested():
                existing = existing_by_number.get(number)
                if existing:
                    _apply_incident_updates(existing, payload)
                    updated += 1
                else:
                    incident = Incident(**payload)
                    db.add(incident)
                    existing_by_number[number] = incident
                    inserted += 1
                db.flush()
        except SQLAlchemyError:
            failed += 1
            logger.exception("Failed upserting incident %s", number)

    db.commit()

    summary = {
        "success": True,
        "resource": "incidents",
        "total_records_fetched": len(raw_records),
        "inserted": inserted,
        "updated": updated,
        "failed": failed,
    }
    logger.info("Incident sync summary: %s", summary)
    return summary


def _apply_incident_updates(target: Incident, payload: dict[str, Any]) -> None:
    target.short_description = payload["short_description"]
    target.opened_at = payload["opened_at"]
    target.acknowledged_at = payload["acknowledged_at"]
    target.resolved_at = payload["resolved_at"]
    target.closed_at = payload["closed_at"]
    target.priority = payload["priority"]
    target.state = payload["state"]
    target.assignment_group = payload["assignment_group"]
    target.assigned_to = payload["assigned_to"]
    target.vendor = payload["vendor"]
    target.reopen_count = payload["reopen_count"]
    target.sla_due = payload["sla_due"]
    target.resolution_notes = payload["resolution_notes"]


def _transform_incident(raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "number": _as_str(_extract(raw, "number")),
        "short_description": _as_str(_extract(raw, "short_description")),
        "opened_at": _parse_dt(_extract(raw, "opened_at")),
        "acknowledged_at": _parse_dt(
            _extract(raw, "u_acknowledged_at")
            or _extract(raw, "first_response_at")
            or _extract(raw, "work_start")
        ),
        "resolved_at": _parse_dt(_extract(raw, "resolved_at")),
        "closed_at": _parse_dt(_extract(raw, "closed_at")),
        "priority": _as_str(_extract(raw, "priority")),
        "state": _as_str(_extract(raw, "state")),
        "assignment_group": _as_str(_extract(raw, "assignment_group")),
        "assigned_to": _as_str(_extract(raw, "assigned_to")),
        "vendor": _as_str(_extract(raw, "vendor")),
        "reopen_count": _parse_int(_extract(raw, "reopen_count"), default=0),
        "sla_due": _parse_dt(_extract(raw, "sla_due")),
        "resolution_notes": _as_str(_extract(raw, "close_notes") or _extract(raw, "resolution_notes")),
    }


def _extract(raw: dict[str, Any], key: str) -> Any:
    value = raw.get(key)
    if isinstance(value, dict):
        if "display_value" in value and value["display_value"] not in (None, ""):
            return value["display_value"]
        return value.get("value")
    return value


def _as_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _parse_int(value: Any, default: int = 0) -> int:
    if value in (None, ""):
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _parse_dt(value: Any) -> datetime | None:
    text = _as_str(value)
    if not text:
        return None

    formats = ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f")
    for fmt in formats:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue

    if text.endswith("Z"):
        try:
            return datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            return None

    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None
