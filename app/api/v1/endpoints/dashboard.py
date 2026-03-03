from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import JSONResponse

from app.services.dashboard_service import (
    get_engineer_dashboard,
    get_executive_dashboard,
    get_vendor_dashboard,
)
from app.services.servicenow_client import ServiceNowClient, ServiceNowClientError
from app.utils.review_period import parse_period_range

router = APIRouter()


def _dashboard_error_response(exc: ServiceNowClientError) -> JSONResponse:
    if str(exc) == "ServiceNow not configured":
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"error": "ServiceNow not configured"},
        )
    return JSONResponse(
        status_code=status.HTTP_502_BAD_GATEWAY,
        content={"error": str(exc)},
    )


@router.get("/dashboard/executive", summary="Executive dashboard metrics")
async def executive_dashboard(
    period: str = Query("1d"),
    page: int = Query(1, ge=1),
    size: int = Query(25, ge=1, le=500),
) -> Any:
    try:
        range_info = parse_period_range(period)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    client = ServiceNowClient()
    try:
        return get_executive_dashboard(
            client=client,
            start_time=range_info.start_time,
            period_code=range_info.code,
            page=page,
            size=size,
        )
    except ServiceNowClientError as exc:
        return _dashboard_error_response(exc)


@router.get("/dashboard/vendor/{vendor_name}", summary="Vendor dashboard metrics")
async def vendor_dashboard(
    vendor_name: str,
    period: str = Query("1d"),
) -> Any:
    try:
        range_info = parse_period_range(period)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    client = ServiceNowClient()
    try:
        return get_vendor_dashboard(
            client=client,
            vendor_name=vendor_name,
            start_time=range_info.start_time,
            period_code=range_info.code,
        )
    except ServiceNowClientError as exc:
        return _dashboard_error_response(exc)


@router.get("/dashboard/engineer/{engineer_name}", summary="Engineer dashboard metrics")
async def engineer_dashboard(
    engineer_name: str,
    period: str = Query("1d"),
) -> Any:
    try:
        range_info = parse_period_range(period)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    client = ServiceNowClient()
    try:
        return get_engineer_dashboard(
            client=client,
            engineer_name=engineer_name,
            start_time=range_info.start_time,
            period_code=range_info.code,
        )
    except ServiceNowClientError as exc:
        return _dashboard_error_response(exc)
