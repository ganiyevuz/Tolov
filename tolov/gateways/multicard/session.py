"""Token-managed Multicard sessions (sync + async).

Owns credentials + the JWT (fetch/cache/refresh) and injects
``Authorization: Bearer``. Unwraps the {success,data,error} envelope.
"""
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from loguru import logger

from tolov.core.http import HttpClient, AsyncHttpClient
from tolov.core.exceptions import (
    ExternalServiceError,
    TransactionNotFound,
    InvalidAmount,
)
from tolov.gateways.multicard.constants import (
    MulticardNetworks,
    MulticardEndpoints,
    MulticardErrors,
)

GMT5 = timezone(timedelta(hours=5))

_ERROR_MAP = {
    MulticardErrors.NOT_FOUND: TransactionNotFound,
    MulticardErrors.CARD_NOT_FOUND: TransactionNotFound,
    MulticardErrors.FIELDS: InvalidAmount,
}


def map_error(envelope: Dict[str, Any]) -> None:
    """Raise a mapped exception from a {success: false, error} envelope."""
    err = (envelope or {}).get("error") or {}
    code = err.get("code", MulticardErrors.UNKNOWN)
    details = err.get("details", "")
    exc_cls = _ERROR_MAP.get(code, ExternalServiceError)
    raise exc_cls(message=f"{code}: {details}", code=code, data=err)


def unwrap(payload: Dict[str, Any]) -> Any:
    """Return data on success, else raise mapped exception."""
    if isinstance(payload, dict) and payload.get("success"):
        return payload.get("data")
    map_error(payload)


def _parse_expiry(value: str) -> datetime:
    """Parse Multicard token expiry ("YYYY-MM-DD HH:MM:SS", GMT+5)."""
    return datetime.strptime(value, "%Y-%m-%d %H:%M:%S").replace(tzinfo=GMT5)


class MulticardSession:
    """Synchronous token-managed Multicard session."""

    def __init__(self, application_id, secret, is_test_mode=False, timeout=30):
        self.application_id = application_id
        self.secret = secret
        base = MulticardNetworks.TEST_NET if is_test_mode else MulticardNetworks.PROD_NET
        self._http = HttpClient(
            base_url=base,
            headers={"Content-Type": "application/json"},
            timeout=timeout,
        )
        self._token: Optional[str] = None
        self._expiry: Optional[datetime] = None

    # --- token lifecycle ---
    def _token_valid(self) -> bool:
        if not self._token or not self._expiry:
            return False
        return datetime.now(GMT5) < (self._expiry - timedelta(seconds=30))

    def _fetch_token(self) -> None:
        body = {"application_id": self.application_id, "secret": self.secret}
        try:
            payload = self._http.post(MulticardEndpoints.AUTH, json_data=body)
        except ExternalServiceError as exc:
            data = getattr(exc, "data", None)
            if isinstance(data, dict) and "error" in data:
                map_error(data)
            raise
        data = unwrap(payload)
        self._token = data["token"]
        self._expiry = _parse_expiry(data["expiry"])
        logger.debug("Multicard token refreshed, expires {}", self._expiry)

    def _auth_headers(self) -> Dict[str, str]:
        if not self._token_valid():
            self._fetch_token()
        return {"Authorization": f"Bearer {self._token}"}

    # --- requests ---
    def request(self, method, endpoint, json_data=None, params=None, _retry=True):
        headers = self._auth_headers()
        try:
            payload = self._http.request(
                method,
                endpoint,
                json_data=json_data,
                params=params,
                headers=headers,
            )
        except ExternalServiceError as exc:
            if _retry and "HTTP error: 401" in str(exc):
                self._token = None
                return self.request(method, endpoint, json_data, params, _retry=False)
            data = getattr(exc, "data", None)
            if isinstance(data, dict) and "error" in data:
                map_error(data)
            raise
        return unwrap(payload)

    def get(self, endpoint, params=None):
        return self.request("GET", endpoint, params=params)

    def post(self, endpoint, json_data=None):
        return self.request("POST", endpoint, json_data=json_data)

    def put(self, endpoint, json_data=None):
        return self.request("PUT", endpoint, json_data=json_data)

    def patch(self, endpoint, json_data=None):
        return self.request("PATCH", endpoint, json_data=json_data)

    def delete(self, endpoint, json_data=None):
        return self.request("DELETE", endpoint, json_data=json_data)


class AsyncMulticardSession(MulticardSession):
    """Async token-managed session — overrides HTTP-calling methods."""

    def __init__(self, application_id, secret, is_test_mode=False, timeout=30):
        self.application_id = application_id
        self.secret = secret
        base = MulticardNetworks.TEST_NET if is_test_mode else MulticardNetworks.PROD_NET
        self._http = AsyncHttpClient(
            base_url=base,
            headers={"Content-Type": "application/json"},
            timeout=timeout,
        )
        self._token = None
        self._expiry = None

    async def _fetch_token(self) -> None:
        body = {"application_id": self.application_id, "secret": self.secret}
        try:
            payload = await self._http.post(MulticardEndpoints.AUTH, json_data=body)
        except ExternalServiceError as exc:
            data = getattr(exc, "data", None)
            if isinstance(data, dict) and "error" in data:
                map_error(data)
            raise
        data = unwrap(payload)
        self._token = data["token"]
        self._expiry = _parse_expiry(data["expiry"])
        logger.debug("Multicard token refreshed, expires {}", self._expiry)

    async def _auth_headers(self) -> Dict[str, str]:
        if not self._token_valid():
            await self._fetch_token()
        return {"Authorization": f"Bearer {self._token}"}

    async def request(self, method, endpoint, json_data=None, params=None, _retry=True):
        headers = await self._auth_headers()
        try:
            payload = await self._http.request(
                method,
                endpoint,
                json_data=json_data,
                params=params,
                headers=headers,
            )
        except ExternalServiceError as exc:
            if _retry and "HTTP error: 401" in str(exc):
                self._token = None
                return await self.request(
                    method, endpoint, json_data, params, _retry=False
                )
            data = getattr(exc, "data", None)
            if isinstance(data, dict) and "error" in data:
                map_error(data)
            raise
        return unwrap(payload)

    async def get(self, endpoint, params=None):
        return await self.request("GET", endpoint, params=params)

    async def post(self, endpoint, json_data=None):
        return await self.request("POST", endpoint, json_data=json_data)

    async def put(self, endpoint, json_data=None):
        return await self.request("PUT", endpoint, json_data=json_data)

    async def patch(self, endpoint, json_data=None):
        return await self.request("PATCH", endpoint, json_data=json_data)

    async def delete(self, endpoint, json_data=None):
        return await self.request("DELETE", endpoint, json_data=json_data)
