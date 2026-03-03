from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.incident import Incident, SLARecord
from app.models.performance import EngineerPerformance, VendorPerformance

MAX_SLA_RECORDS = 5000


@dataclass
class GroupMetrics:
    total_incidents: int = 0
    resolved_incidents: int = 0
    breached_slas: int = 0
    reopened_incidents: int = 0
    breach_p1: int = 0
    breach_p2: int = 0
    breach_p3: int = 0
    breach_p4: int = 0
    backlog_over_7_days: int = 0
    mttr_hours_sum: float = 0.0
    mttr_count: int = 0
    mtta_hours_sum: float = 0.0
    mtta_count: int = 0

    @property
    def sla_adherence_pct(self) -> float:
        if self.total_incidents == 0:
            return 0.0
        return round(
            ((self.total_incidents - self.breached_slas) / self.total_incidents) * 100.0,
            2,
        )

    @property
    def mttr_hours(self) -> float | None:
        if self.mttr_count == 0:
            return None
        return round(self.mttr_hours_sum / self.mttr_count, 2)

    @property
    def mtta_hours(self) -> float | None:
        if self.mtta_count == 0:
            return None
        return round(self.mtta_hours_sum / self.mtta_count, 2)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_incidents": self.total_incidents,
            "resolved_incidents": self.resolved_incidents,
            "breached_slas": self.breached_slas,
            "sla_adherence_pct": self.sla_adherence_pct,
            "mttr_hours": self.mttr_hours,
            "mtta_hours": self.mtta_hours,
            "breach_p1": self.breach_p1,
            "breach_p2": self.breach_p2,
            "breach_p3": self.breach_p3,
            "breach_p4": self.breach_p4,
            "backlog_over_7_days": self.backlog_over_7_days,
            "reopened_incidents": self.reopened_incidents,
            "avg_resolution_hours": self.mttr_hours,
        }


def calculate_sla_summary(
    db: Session,
    start_time: datetime,
    period_code: str,
) -> dict[str, Any]:
    incidents = db.execute(
        select(Incident)
        .where(Incident.opened_at >= start_time)
        .order_by(Incident.opened_at.desc())
        .limit(MAX_SLA_RECORDS)
    ).scalars().all()
    incident_numbers = [x.number for x in incidents]
    if incident_numbers:
        sla_records = db.execute(
            select(SLARecord).where(SLARecord.incident_number.in_(incident_numbers))
        ).scalars().all()
    else:
        sla_records = []
    breached_numbers = {row.incident_number for row in sla_records if row.breached}

    period_start, period_end = _resolve_period(incidents)
    now = datetime.now(UTC)
    backlog_cutoff = now - timedelta(days=7)

    vendor_groups: dict[str, GroupMetrics] = defaultdict(GroupMetrics)
    engineer_groups: dict[str, GroupMetrics] = defaultdict(GroupMetrics)
    overall = GroupMetrics()

    for incident in incidents:
        vendor_key = (incident.vendor or "UNKNOWN_VENDOR").strip() or "UNKNOWN_VENDOR"
        engineer_key = (incident.assigned_to or "UNASSIGNED").strip() or "UNASSIGNED"
        is_breached = incident.number in breached_numbers
        priority = _normalize_priority(incident.priority)

        _accumulate(
            metrics=overall,
            incident=incident,
            is_breached=is_breached,
            priority=priority,
            backlog_cutoff=backlog_cutoff,
        )
        _accumulate(
            metrics=vendor_groups[vendor_key],
            incident=incident,
            is_breached=is_breached,
            priority=priority,
            backlog_cutoff=backlog_cutoff,
        )
        _accumulate(
            metrics=engineer_groups[engineer_key],
            incident=incident,
            is_breached=is_breached,
            priority=priority,
            backlog_cutoff=backlog_cutoff,
        )

    vendor_rows = _persist_vendor_performance(db, vendor_groups, period_start, period_end)
    engineer_rows = _persist_engineer_performance(db, engineer_groups, period_start, period_end)
    db.commit()

    return {
        "success": True,
        "loading_status": "complete",
        "period": period_code,
        "period_start": str(period_start),
        "period_end": str(period_end),
        "overall": {
            "total_incidents": overall.total_incidents,
            "mttr_hours": overall.mttr_hours,
            "mtta_hours": overall.mtta_hours,
            "backlog_over_7_days": overall.backlog_over_7_days,
            "breach_count_by_priority": {
                "P1": overall.breach_p1,
                "P2": overall.breach_p2,
                "P3": overall.breach_p3,
                "P4": overall.breach_p4,
            },
        },
        "vendor_performance": vendor_rows,
        "engineer_performance": engineer_rows,
    }


def _persist_vendor_performance(
    db: Session,
    groups: dict[str, GroupMetrics],
    period_start: date,
    period_end: date,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for vendor, metrics in groups.items():
        existing = db.execute(
            select(VendorPerformance).where(
                VendorPerformance.vendor == vendor,
                VendorPerformance.period_start == period_start,
                VendorPerformance.period_end == period_end,
            )
        ).scalar_one_or_none()

        payload = metrics.to_dict()
        if existing:
            _apply_perf_payload(existing, payload)
            row = existing
        else:
            row = VendorPerformance(
                vendor=vendor,
                period_start=period_start,
                period_end=period_end,
                **payload,
            )
            db.add(row)
        rows.append({"vendor": vendor, **payload})
    return rows


def _persist_engineer_performance(
    db: Session,
    groups: dict[str, GroupMetrics],
    period_start: date,
    period_end: date,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for engineer_name, metrics in groups.items():
        existing = db.execute(
            select(EngineerPerformance).where(
                EngineerPerformance.engineer_name == engineer_name,
                EngineerPerformance.period_start == period_start,
                EngineerPerformance.period_end == period_end,
            )
        ).scalar_one_or_none()

        payload = metrics.to_dict()
        if existing:
            _apply_perf_payload(existing, payload)
            row = existing
        else:
            row = EngineerPerformance(
                engineer_name=engineer_name,
                period_start=period_start,
                period_end=period_end,
                **payload,
            )
            db.add(row)
        rows.append({"engineer_name": engineer_name, **payload})
    return rows


def _apply_perf_payload(target: VendorPerformance | EngineerPerformance, payload: dict[str, Any]) -> None:
    target.total_incidents = payload["total_incidents"]
    target.resolved_incidents = payload["resolved_incidents"]
    target.breached_slas = payload["breached_slas"]
    target.sla_adherence_pct = payload["sla_adherence_pct"]
    target.mttr_hours = payload["mttr_hours"]
    target.mtta_hours = payload["mtta_hours"]
    target.breach_p1 = payload["breach_p1"]
    target.breach_p2 = payload["breach_p2"]
    target.breach_p3 = payload["breach_p3"]
    target.breach_p4 = payload["breach_p4"]
    target.backlog_over_7_days = payload["backlog_over_7_days"]
    target.reopened_incidents = payload["reopened_incidents"]
    target.avg_resolution_hours = payload["avg_resolution_hours"]


def _accumulate(
    metrics: GroupMetrics,
    incident: Incident,
    is_breached: bool,
    priority: str,
    backlog_cutoff: datetime,
) -> None:
    opened_at = _to_utc(incident.opened_at)
    acknowledged_at = _to_utc(incident.acknowledged_at)
    resolved_at = _to_utc(incident.resolved_at or incident.closed_at)

    metrics.total_incidents += 1
    if incident.reopen_count > 0:
        metrics.reopened_incidents += 1

    if is_breached:
        metrics.breached_slas += 1
        if priority == "P1":
            metrics.breach_p1 += 1
        elif priority == "P2":
            metrics.breach_p2 += 1
        elif priority == "P3":
            metrics.breach_p3 += 1
        elif priority == "P4":
            metrics.breach_p4 += 1

    if opened_at and resolved_at and resolved_at >= opened_at:
        metrics.resolved_incidents += 1
        metrics.mttr_hours_sum += (resolved_at - opened_at).total_seconds() / 3600.0
        metrics.mttr_count += 1

    if opened_at and acknowledged_at and acknowledged_at >= opened_at:
        metrics.mtta_hours_sum += (acknowledged_at - opened_at).total_seconds() / 3600.0
        metrics.mtta_count += 1

    is_open = incident.resolved_at is None and incident.closed_at is None
    if is_open and opened_at and opened_at < backlog_cutoff:
        metrics.backlog_over_7_days += 1


def _normalize_priority(priority: str | None) -> str:
    if not priority:
        return "P4"
    p = priority.upper()
    if "1" in p or "P1" in p or "CRITICAL" in p:
        return "P1"
    if "2" in p or "P2" in p or "HIGH" in p:
        return "P2"
    if "3" in p or "P3" in p or "MODERATE" in p or "MEDIUM" in p:
        return "P3"
    return "P4"


def _resolve_period(incidents: list[Incident]) -> tuple[date, date]:
    today = datetime.now(UTC).date()
    if not incidents:
        return today, today

    opened_dates = [item.opened_at.date() for item in incidents if item.opened_at]
    if not opened_dates:
        return today, today
    return min(opened_dates), max(opened_dates)


def _to_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
