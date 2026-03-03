from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.services.duplicate_engine import detect_and_store_duplicates
from app.services.governance_checks import generate_governance_report
from app.services.sla_engine import calculate_sla_summary
from app.utils.review_period import parse_period_range

router = APIRouter()


@router.get("/analytics/sla-summary", summary="Calculate and persist SLA governance summary")
async def sla_summary(
    period: str = Query("1d"),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    try:
        range_info = parse_period_range(period)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    return calculate_sla_summary(
        db,
        start_time=range_info.start_time,
        period_code=range_info.code,
    )


@router.get("/analytics/governance-report", summary="Generate governance quality report")
async def governance_report(
    period: str = Query("1d"),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    try:
        range_info = parse_period_range(period)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    return generate_governance_report(
        db,
        start_time=range_info.start_time,
        period_code=range_info.code,
    )


@router.get("/analytics/duplicates", summary="Detect and persist duplicate incidents")
def duplicate_report(db: Session = Depends(get_db)) -> dict[str, Any]:
    return detect_and_store_duplicates(db)
