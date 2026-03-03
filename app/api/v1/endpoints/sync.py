from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.services.servicenow_client import ServiceNowClient, ServiceNowClientError
from app.services.sync_service import build_servicenow_client, run_incident_sync
from app.utils.config import get_settings
from app.utils.review_period import parse_period_range

router = APIRouter()


def _build_servicenow_client() -> ServiceNowClient:
    settings = get_settings()
    return build_servicenow_client(settings)


@router.get("/sync/incidents", summary="Sync incidents from ServiceNow")
def sync_incidents(period: str = Query("1d")) -> dict[str, Any]:
    client = _build_servicenow_client()
    try:
        range_info = parse_period_range(period)
        return client.fetch_incidents(start_time=range_info.start_time, max_records=500)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except ServiceNowClientError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"success": False, "error": str(exc), "resource": "incidents"},
        ) from exc


@router.post("/sync/run", summary="Run incident synchronization job")
def run_sync(
    period: str = Query("1d"),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    client = _build_servicenow_client()
    try:
        range_info = parse_period_range(period)
        return run_incident_sync(
            db=db,
            client=client,
            start_time=range_info.start_time,
            max_records=500,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except ServiceNowClientError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"success": False, "error": str(exc), "resource": "incidents"},
        ) from exc
