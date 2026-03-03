from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Any

from app.services.servicenow_client import ServiceNowClient, ServiceNowClientError

MAX_ANALYTICS_RECORDS = 5000


def get_executive_dashboard(
    client: ServiceNowClient,
    start_time: datetime,
    period_code: str,
    page: int = 1,
    size: int = 25,
) -> dict[str, Any]:
    page, size = _sanitize_paging(page, size)
    incidents = _fetch_period_incidents(client=client, start_time=start_time)

    total = len(incidents)
    breached = sum(1 for row in incidents if _is_breached(row))
    overall_sla_pct = _pct(total - breached, total)

    total_open_tickets = sum(1 for row in incidents if _is_open_ticket(row))
    breach_trend = _build_breach_trend(incidents, days=14)
    all_ranking = _build_vendor_ranking(incidents)
    paged_ranking = _paginate_list(all_ranking, page, size)

    return {
        "success": True,
        "loading_status": "complete",
        "period": period_code,
        "data": {
            "overall_sla_pct": overall_sla_pct,
            "total_open_tickets": total_open_tickets,
            "breach_trend": breach_trend,
            "vendor_ranking": paged_ranking,
        },
        "pagination": {
            "page": page,
            "size": size,
            "total_records": len(all_ranking),
            "total_pages": _total_pages(len(all_ranking), size),
        },
    }


def get_vendor_dashboard(
    client: ServiceNowClient,
    vendor_name: str,
    start_time: datetime,
    period_code: str,
) -> dict[str, Any]:
    incidents = _fetch_period_incidents(client=client, start_time=start_time)
    selected = [row for row in incidents if _normalized_vendor(row).lower() == vendor_name.lower()]

    total = len(selected)
    breach_count = sum(1 for row in selected if _is_breached(row))
    reopened = sum(1 for row in selected if _to_int(_extract(row, "reopen_count")) > 0)
    mttr_hours = _avg(
        [
            value
            for value in (_calculate_mttr_hours(row) for row in selected)
            if value is not None
        ]
    )

    return {
        "success": True,
        "loading_status": "complete",
        "period": period_code,
        "data": {
            "vendor_name": vendor_name,
            "sla_pct": _pct(total - breach_count, total),
            "mttr_hours": mttr_hours,
            "reopen_pct": _pct(reopened, total),
            "breach_count": breach_count,
            "total_tickets": total,
        },
    }


def get_engineer_dashboard(
    client: ServiceNowClient,
    engineer_name: str,
    start_time: datetime,
    period_code: str,
) -> dict[str, Any]:
    incidents = _fetch_period_incidents(client=client, start_time=start_time)
    selected = [row for row in incidents if _normalized_assignee(row).lower() == engineer_name.lower()]

    tickets_handled = len(selected)
    breach_count = sum(1 for row in selected if _is_breached(row))
    reopened = sum(1 for row in selected if _to_int(_extract(row, "reopen_count")) > 0)
    sla_pct = _pct(tickets_handled - breach_count, tickets_handled)
    reopen_pct = _pct(reopened, tickets_handled)
    productivity_score = _calculate_productivity_score(sla_pct, reopen_pct, tickets_handled)

    return {
        "success": True,
        "loading_status": "complete",
        "period": period_code,
        "data": {
            "engineer_name": engineer_name,
            "tickets_handled": tickets_handled,
            "sla_pct": sla_pct,
            "reopen_pct": reopen_pct,
            "productivity_score": productivity_score,
        },
    }


def _fetch_period_incidents(client: ServiceNowClient, start_time: datetime) -> list[dict[str, Any]]:
    payload = client.fetch_incidents(start_time=start_time, max_records=MAX_ANALYTICS_RECORDS)
    records = payload.get("data", [])
    if not isinstance(records, list):
        raise ServiceNowClientError("Invalid ServiceNow incident payload")
    return records


def _build_vendor_ranking(incidents: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_vendor: dict[str, dict[str, Any]] = {}
    for row in incidents:
        vendor = _normalized_vendor(row)
        bucket = by_vendor.setdefault(vendor, {"total": 0, "breach": 0, "mttr_values": []})
        bucket["total"] += 1
        if _is_breached(row):
            bucket["breach"] += 1
        mttr = _calculate_mttr_hours(row)
        if mttr is not None:
            bucket["mttr_values"].append(mttr)

    ranking: list[dict[str, Any]] = []
    for vendor, values in by_vendor.items():
        ranking.append(
            {
                "vendor": vendor,
                "sla_pct": _pct(values["total"] - values["breach"], values["total"]),
                "mttr_hours": _avg(values["mttr_values"]),
                "breach_count": values["breach"],
            }
        )

    ranking.sort(key=lambda x: (-x["sla_pct"], x["breach_count"], x["vendor"]))
    return ranking


def _build_breach_trend(
    incidents: list[dict[str, Any]],
    days: int = 14,
) -> list[dict[str, Any]]:
    today = datetime.now(UTC).date()
    start = today - timedelta(days=days - 1)
    counts = {start + timedelta(days=i): 0 for i in range(days)}

    for incident in incidents:
        if not _is_breached(incident):
            continue
        opened = _incident_date(incident)
        if opened is not None and start <= opened <= today:
            counts[opened] += 1

    return [{"date": str(day), "breach_count": counts[day]} for day in sorted(counts)]


def _incident_date(incident: dict[str, Any]) -> date | None:
    parsed = _parse_dt(_extract(incident, "opened_at") or _extract(incident, "sys_created_on"))
    if parsed is None:
        return None
    return parsed.date()


def _is_open_ticket(row: dict[str, Any]) -> bool:
    if _parse_dt(_extract(row, "resolved_at")) or _parse_dt(_extract(row, "closed_at")):
        return False
    state = (_as_str(_extract(row, "state")) or "").lower()
    return state not in {"6", "7", "resolved", "closed", "cancelled", "canceled"}


def _is_breached(row: dict[str, Any]) -> bool:
    made_sla = (_as_str(_extract(row, "made_sla")) or "").lower()
    if made_sla in {"false", "0", "no"}:
        return True

    breach_markers = [
        _extract(row, "sla_breach"),
        _extract(row, "breached"),
        _extract(row, "u_sla_breached"),
    ]
    if any(_is_truthy(marker) for marker in breach_markers):
        return True

    breach_count = _to_int(_extract(row, "breach_count"))
    return breach_count > 0


def _calculate_mttr_hours(row: dict[str, Any]) -> float | None:
    opened = _parse_dt(_extract(row, "opened_at") or _extract(row, "sys_created_on"))
    resolved = _parse_dt(_extract(row, "resolved_at") or _extract(row, "closed_at"))
    if opened is None or resolved is None or resolved < opened:
        return None
    return (resolved - opened).total_seconds() / 3600.0


def _normalized_vendor(row: dict[str, Any]) -> str:
    for key in ("vendor", "company", "u_vendor", "assignment_group"):
        value = _as_str(_extract(row, key))
        if value:
            return value
    return "UNKNOWN_VENDOR"


def _normalized_assignee(row: dict[str, Any]) -> str:
    for key in ("assigned_to", "caller_id", "opened_by"):
        value = _as_str(_extract(row, key))
        if value:
            return value
    return "UNKNOWN_ENGINEER"


def _extract(raw: dict[str, Any], key: str) -> Any:
    value = raw.get(key)
    if isinstance(value, dict):
        display = value.get("display_value")
        if display not in (None, ""):
            return display
        return value.get("value")
    return value


def _as_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _to_int(value: Any) -> int:
    text = _as_str(value)
    if not text:
        return 0
    try:
        return int(float(text))
    except (TypeError, ValueError):
        return 0


def _is_truthy(value: Any) -> bool:
    text = (_as_str(value) or "").lower()
    return text in {"true", "1", "yes", "y"}


def _parse_dt(value: Any) -> datetime | None:
    text = _as_str(value)
    if not text:
        return None

    formats = ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f")
    for fmt in formats:
        try:
            parsed = datetime.strptime(text, fmt)
            return parsed.replace(tzinfo=UTC)
        except ValueError:
            continue

    if text.endswith("Z"):
        try:
            return datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            return None

    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _paginate_list(items: list[dict[str, Any]], page: int, size: int) -> list[dict[str, Any]]:
    start = (page - 1) * size
    end = start + size
    return items[start:end]


def _total_pages(total: int, size: int) -> int:
    if total == 0:
        return 0
    return ((total - 1) // size) + 1


def _sanitize_paging(page: int, size: int) -> tuple[int, int]:
    clean_page = max(1, page)
    clean_size = max(1, min(size, 500))
    return clean_page, clean_size


def _pct(num: int | float, den: int | float) -> float:
    if den == 0:
        return 0.0
    return round((num / den) * 100.0, 2)


def _avg(values: list[float]) -> float | None:
    if not values:
        return None
    return round(sum(values) / len(values), 2)


def _calculate_productivity_score(sla_pct: float, reopen_pct: float, tickets_handled: int) -> float:
    volume_score = min(float(tickets_handled), 100.0)
    score = (sla_pct * 0.6) + ((100.0 - reopen_pct) * 0.3) + (volume_score * 0.1)
    return round(max(0.0, min(score, 100.0)), 2)

