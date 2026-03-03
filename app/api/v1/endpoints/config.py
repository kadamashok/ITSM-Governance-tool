from __future__ import annotations

import logging
from urllib.parse import urlsplit
from typing import Any

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from app.services.servicenow_client import ServiceNowClientError
from app.services.servicenow_config_store import get_status, save_oauth_settings
from app.services.servicenow_oauth_service import (
    build_microsoft_authorize_url,
    exchange_code_for_tokens,
)
from app.utils.config import get_settings

router = APIRouter()
logger = logging.getLogger(__name__)


class ServiceNowOAuthConfigRequest(BaseModel):
    instance_url: str
    client_id: str
    client_secret: str
    tenant_id: str
    oauth_scope: str


def normalize_servicenow_instance_url(raw_url: str) -> str:
    cleaned = (raw_url or "").strip()
    if not cleaned:
        raise ValueError("ServiceNow instance URL is required")

    parsed = urlsplit(cleaned)
    scheme = parsed.scheme.lower()
    host = parsed.netloc.lower()
    path = (parsed.path or "").rstrip("/")

    if scheme != "https":
        raise ValueError("ServiceNow instance URL must start with https://")
    if not host or not host.endswith(".service-now.com"):
        raise ValueError("Invalid ServiceNow instance URL. Please use base instance URL (without /sp).")
    if path.lower() == "/sp":
        path = ""
    if path != "" or parsed.query or parsed.fragment:
        raise ValueError("Invalid ServiceNow instance URL. Please use base instance URL (without /sp).")
    return f"https://{host}"


@router.post("/config/servicenow", summary="Save ServiceNow OAuth configuration")
def configure_servicenow_oauth(
    payload: ServiceNowOAuthConfigRequest,
) -> dict[str, Any]:
    try:
        instance_url = normalize_servicenow_instance_url(payload.instance_url)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error": str(exc)},
        ) from exc

    client_id = payload.client_id.strip()
    client_secret = payload.client_secret.strip()
    tenant_id = payload.tenant_id.strip()
    oauth_scope = payload.oauth_scope.strip()

    if not client_id or not client_secret or not tenant_id or not oauth_scope:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error": "Client ID, Client Secret, Tenant ID, and OAuth Scope are required"},
        )

    save_oauth_settings(
        instance_url=instance_url,
        client_id=client_id,
        client_secret=client_secret,
        tenant_id=tenant_id,
        oauth_scope=oauth_scope,
    )
    logger.info("Stored ServiceNow OAuth configuration for instance=%s tenant=%s", instance_url, tenant_id)
    return {
        "success": True,
        "message": "OAuth settings saved. Continue with Microsoft login.",
        "auth_start_url": "/auth/login",
    }


@router.get("/auth/login", summary="Redirect to Microsoft OAuth login")
def auth_login() -> RedirectResponse:
    try:
        authorize_url = build_microsoft_authorize_url()
    except ServiceNowClientError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": str(exc)},
        ) from exc
    return RedirectResponse(url=authorize_url, status_code=status.HTTP_302_FOUND)


@router.get("/auth/callback", summary="Microsoft OAuth callback")
def auth_callback(
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
    error_description: str | None = Query(default=None),
) -> RedirectResponse:
    settings = get_settings()
    base = settings.frontend_base_url.rstrip("/")
    redirect_error = f"{base}/settings/servicenow?oauth=error"
    redirect_success = f"{base}/executive"

    if error:
        logger.warning("Microsoft OAuth returned error: %s (%s)", error, error_description or "no_description")
        return RedirectResponse(url=f"{redirect_error}&reason=oauth_failed", status_code=status.HTTP_302_FOUND)

    if not code or not state:
        return RedirectResponse(url=f"{redirect_error}&reason=missing_code", status_code=status.HTTP_302_FOUND)

    try:
        exchange_code_for_tokens(code=code, state=state)
    except ServiceNowClientError as exc:
        logger.warning("OAuth callback token exchange failed: %s", str(exc))
        return RedirectResponse(url=f"{redirect_error}&reason=token_exchange", status_code=status.HTTP_302_FOUND)

    logger.info("Microsoft OAuth callback completed successfully")
    return RedirectResponse(url=redirect_success, status_code=status.HTTP_302_FOUND)


@router.get("/config/status", summary="Get ServiceNow connection status")
def config_status() -> dict[str, Any]:
    status_payload = get_status()
    return {
        "connected": bool(status_payload["connected"]),
        "instance_url": status_payload["instance_url"],
        "token_expires_at": status_payload["token_expires_at"],
    }
