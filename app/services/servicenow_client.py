from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

import requests
from requests.exceptions import RequestException

from app.services.servicenow_exceptions import ServiceNowClientError
from app.services.servicenow_config_store import get_oauth_config
from app.services.servicenow_oauth_service import get_valid_access_token
from app.utils.review_period import build_servicenow_sysparm_query


logger = logging.getLogger(__name__)


class ServiceNowClient:
    def __init__(
        self,
        instance_url: str | None = None,
        access_token: str | None = None,
        timeout_seconds: int = 30,
        page_size: int = 100,
    ) -> None:
        self._instance_url = (instance_url or "").rstrip("/")
        self._access_token = access_token
        self.timeout_seconds = timeout_seconds
        self.page_size = max(1, min(page_size, 500))
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json"})

    def test_connection(self) -> None:
        self._request("GET", "/api/now/table/incident", params={"sysparm_limit": 1})

    def fetch_incidents(
        self,
        start_time: datetime | None = None,
        max_records: int = 500,
    ) -> dict[str, Any]:
        return self._fetch_paginated(
            endpoint="/api/now/table/incident",
            label="incidents",
            start_time=start_time,
            max_records=max_records,
        )

    def fetch_service_requests(
        self,
        start_time: datetime | None = None,
        max_records: int = 500,
    ) -> dict[str, Any]:
        return self._fetch_paginated(
            endpoint="/api/now/table/sc_request",
            label="service_requests",
            start_time=start_time,
            max_records=max_records,
        )

    def fetch_sla_records(
        self,
        start_time: datetime | None = None,
        max_records: int = 500,
    ) -> dict[str, Any]:
        return self._fetch_paginated(
            endpoint="/api/now/table/task_sla",
            label="sla_records",
            start_time=start_time,
            max_records=max_records,
        )

    def _fetch_paginated(
        self,
        endpoint: str,
        label: str,
        start_time: datetime | None = None,
        max_records: int = 500,
    ) -> dict[str, Any]:
        records: list[dict[str, Any]] = []
        offset = 0
        pages_fetched = 0
        capped_records = max(1, min(max_records, 5000))

        while True:
            params: dict[str, Any] = {
                "sysparm_limit": self.page_size,
                "sysparm_offset": offset,
            }
            if start_time is not None:
                params["sysparm_query"] = build_servicenow_sysparm_query(start_time)

            payload = self._request("GET", endpoint, params=params)
            page_records = payload.get("result", [])
            if not isinstance(page_records, list):
                logger.error("Unexpected ServiceNow payload shape for %s", label)
                raise ServiceNowClientError(f"Unexpected payload while fetching {label}")

            records.extend(page_records[: max(0, capped_records - len(records))])
            pages_fetched += 1

            if len(records) >= capped_records or len(page_records) < self.page_size:
                break
            offset += self.page_size

        return {
            "success": True,
            "resource": label,
            "count": len(records),
            "pages_fetched": pages_fetched,
            "data": records,
        }

    def _resolve_auth(self) -> tuple[str, str]:
        if self._instance_url and self._access_token:
            return self._instance_url, self._access_token
        instance_url = self._instance_url
        if not instance_url:
            cfg = get_oauth_config()
            if cfg is None:
                raise ServiceNowClientError("ServiceNow not configured")
            instance_url = cfg["instance_url"]
        token = get_valid_access_token()
        return instance_url, token

    def _request(
        self,
        method: str,
        endpoint: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        instance_url, access_token = self._resolve_auth()
        url = f"{instance_url}{endpoint}"
        self.session.auth = None
        self.session.headers["Authorization"] = f"Bearer {access_token}"

        try:
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                timeout=self.timeout_seconds,
            )
        except RequestException as exc:
            logger.exception("ServiceNow request failed: %s", url)
            raise ServiceNowClientError("ServiceNow request failed") from exc

        if response.status_code >= 400:
            logger.error("ServiceNow API error %s for %s", response.status_code, url)
            if response.status_code in (401, 403):
                raise ServiceNowClientError("Authentication failed", status_code=401)
            if response.status_code == 404:
                raise ServiceNowClientError("Invalid ServiceNow instance URL", status_code=404)
            raise ServiceNowClientError(
                f"ServiceNow API returned status {response.status_code}",
                status_code=response.status_code,
            )

        try:
            return response.json()
        except ValueError as exc:
            logger.exception("Invalid JSON response from ServiceNow for %s", url)
            raise ServiceNowClientError("Invalid JSON response from ServiceNow") from exc
