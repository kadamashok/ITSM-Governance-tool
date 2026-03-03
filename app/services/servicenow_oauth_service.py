from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlencode

import requests

from app.services.servicenow_exceptions import ServiceNowClientError
from app.services.servicenow_config_store import (
    consume_oauth_state,
    get_oauth_config,
    get_token_bundle,
    set_oauth_state,
    update_tokens,
)
from app.utils.config import get_settings


def build_microsoft_authorize_url() -> str:
    cfg = get_oauth_config()
    if cfg is None:
        raise ServiceNowClientError("ServiceNow OAuth is not configured")

    settings = get_settings()
    nonce = secrets.token_urlsafe(32)
    set_oauth_state(nonce=nonce, expires_at=datetime.now(UTC) + timedelta(minutes=10))

    params = {
        "client_id": cfg["client_id"],
        "response_type": "code",
        "redirect_uri": settings.servicenow_oauth_redirect_uri,
        "response_mode": "query",
        "scope": cfg["oauth_scope"],
        "state": nonce,
    }
    tenant = cfg["tenant_id"]
    query = urlencode(params)
    return f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize?{query}"


def exchange_code_for_tokens(code: str, state: str) -> None:
    if not consume_oauth_state(state):
        raise ServiceNowClientError("Invalid or expired OAuth state")
    _request_and_store_tokens(
        grant_type="authorization_code",
        extra_payload={"code": code},
    )


def get_valid_access_token() -> str:
    token_bundle = get_token_bundle()
    if token_bundle is None or not token_bundle.get("access_token"):
        raise ServiceNowClientError("ServiceNow not configured")

    now = datetime.now(UTC)
    expires_at = token_bundle.get("token_expires_at")
    if not isinstance(expires_at, datetime):
        raise ServiceNowClientError("ServiceNow token expiry is unavailable")

    if expires_at <= now + timedelta(seconds=60):
        refresh = token_bundle.get("refresh_token")
        if not isinstance(refresh, str) or not refresh:
            raise ServiceNowClientError("ServiceNow token expired and refresh token is unavailable")
        _request_and_store_tokens(
            grant_type="refresh_token",
            extra_payload={"refresh_token": refresh},
        )
        refreshed = get_token_bundle()
        if refreshed is None or not refreshed.get("access_token"):
            raise ServiceNowClientError("Failed to refresh ServiceNow access token")
        return str(refreshed["access_token"])

    return str(token_bundle["access_token"])


def _request_and_store_tokens(grant_type: str, extra_payload: dict[str, str]) -> None:
    cfg = get_oauth_config()
    if cfg is None:
        raise ServiceNowClientError("ServiceNow OAuth is not configured")

    settings = get_settings()
    tenant = cfg["tenant_id"]
    token_url = f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"
    payload: dict[str, Any] = {
        "grant_type": grant_type,
        "client_id": cfg["client_id"],
        "client_secret": cfg["client_secret"],
        "redirect_uri": settings.servicenow_oauth_redirect_uri,
        "scope": cfg["oauth_scope"],
    }
    payload.update(extra_payload)

    try:
        response = requests.post(token_url, data=payload, timeout=30)
    except requests.RequestException as exc:
        raise ServiceNowClientError("Failed to reach Microsoft token endpoint") from exc

    if response.status_code >= 400:
        if response.status_code in (400, 401):
            raise ServiceNowClientError("Microsoft OAuth authentication failed", status_code=401)
        raise ServiceNowClientError(
            f"Microsoft OAuth token exchange failed with status {response.status_code}",
            status_code=response.status_code,
        )

    try:
        body = response.json()
    except ValueError as exc:
        raise ServiceNowClientError("Invalid OAuth token response") from exc

    access_token = body.get("access_token")
    refresh_token = body.get("refresh_token")
    expires_in = int(body.get("expires_in") or 3600)

    if not isinstance(access_token, str) or not access_token:
        raise ServiceNowClientError("OAuth token response did not include access_token")

    token_expires_at = datetime.now(UTC) + timedelta(seconds=max(30, expires_in))
    update_tokens(
        access_token=access_token,
        refresh_token=refresh_token if isinstance(refresh_token, str) else None,
        token_expires_at=token_expires_at,
    )
