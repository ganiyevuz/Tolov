"""
HTTP client for making requests to payment gateways.
"""
import json
from urllib.parse import urlsplit
from loguru import logger
from typing import Dict, Any, Optional, Union, List

import httpx

from tolov.core.exceptions import (
    ExternalServiceError,
    TimeoutError as PaymentTimeoutError,
    InternalServiceError,
)


def _safe_target(url: Any) -> str:
    """Return ``scheme://host`` for a URL, dropping the path/query.

    Payment request paths can carry secrets (e.g. a card token in
    ``/payment/card/{token}``), so only the host is safe to log or embed in
    error messages.
    """
    parts = urlsplit(str(url))
    return f"{parts.scheme}://{parts.netloc}" if parts.netloc else "(unknown host)"


def _handle_response(response: httpx.Response) -> Dict[str, Any]:
    """
    Handle the response from the API.

    Works for both sync and async clients since httpx.Response
    API is identical in both modes.

    Args:
        response: httpx Response object

    Returns:
        Response data as dictionary

    Raises:
        ExternalServiceError: If the response status code is not 2xx
    """
    try:
        response.raise_for_status()
        return response.json()
    except json.JSONDecodeError:
        logger.error("Failed to decode JSON response (HTTP {})", response.status_code)
        raise InternalServiceError("Failed to decode JSON response")
    except httpx.HTTPStatusError:
        logger.error(
            "HTTP error {} from {}", response.status_code, _safe_target(response.url)
        )
        try:
            error_data = response.json()
        except json.JSONDecodeError:
            error_data = {"raw_response": response.text[:500]}

        raise ExternalServiceError(
            message=f"HTTP error: {response.status_code}", data=error_data
        )


class HttpClient:
    """
    HTTP client for making requests to payment gateways.

    This class provides a simple interface for making HTTP requests to payment
    gateways with proper error handling and logging. Uses a persistent
    httpx.Client for connection pooling.
    """

    def __init__(
        self,
        base_url: str,
        headers: Optional[Dict[str, str]] = None,
        timeout: int = 30,
        verify_ssl: bool = True,
    ):
        self.base_url = base_url.rstrip("/")
        self.headers = headers or {}
        self.timeout = timeout
        self.verify_ssl = verify_ssl
        self._client = httpx.Client(verify=self.verify_ssl)

    def close(self):
        """Close the underlying HTTP client."""
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def _build_url(self, endpoint: str) -> str:
        endpoint = endpoint.lstrip("/")
        return f"{self.base_url}/{endpoint}"

    def request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Union[Dict[str, Any], List[Any]]] = None,
        headers: Optional[Dict[str, str]] = None,
        json_data: Optional[Union[Dict[str, Any], List[Any]]] = None,
        timeout: Optional[int] = None,
    ) -> Dict[str, Any]:
        url = self._build_url(endpoint)
        request_headers = {**self.headers}
        if headers:
            request_headers.update(headers)

        timeout = timeout or self.timeout

        try:
            response = self._client.request(
                method=method.upper(),
                url=url,
                params=params,
                data=data,
                headers=request_headers,
                json=json_data,
                timeout=timeout,
            )
            return _handle_response(response)
        except httpx.TimeoutException:
            target = _safe_target(url)
            logger.error("Request timed out: {} {}", method, target)
            raise PaymentTimeoutError(f"Request timed out: {method} {target}")
        except httpx.ConnectError as exc:
            target = _safe_target(url)
            logger.error("Connection error to {}: {}", target, exc)
            raise ExternalServiceError(f"Connection error to {target}")
        except httpx.HTTPError as exc:
            target = _safe_target(url)
            logger.error("Request error to {} ({})", target, type(exc).__name__)
            raise ExternalServiceError(f"Request error to {target}")

    def get(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None,
    ) -> Dict[str, Any]:
        return self.request(
            method="GET",
            endpoint=endpoint,
            params=params,
            headers=headers,
            timeout=timeout,
        )

    def post(
        self,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None,
    ) -> Dict[str, Any]:
        return self.request(
            method="POST",
            endpoint=endpoint,
            data=data,
            json_data=json_data,
            params=params,
            headers=headers,
            timeout=timeout,
        )

    def put(
        self,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None,
    ) -> Dict[str, Any]:
        return self.request(
            method="PUT",
            endpoint=endpoint,
            data=data,
            json_data=json_data,
            params=params,
            headers=headers,
            timeout=timeout,
        )

    def delete(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None,
    ) -> Dict[str, Any]:
        return self.request(
            method="DELETE",
            endpoint=endpoint,
            params=params,
            headers=headers,
            timeout=timeout,
        )


class AsyncHttpClient:
    """
    Async HTTP client for making requests to payment gateways.

    Uses httpx.AsyncClient for non-blocking HTTP calls, suitable for
    FastAPI and other async frameworks. Uses a persistent client for
    connection pooling.
    """

    def __init__(
        self,
        base_url: str,
        headers: Optional[Dict[str, str]] = None,
        timeout: int = 30,
        verify_ssl: bool = True,
    ):
        self.base_url = base_url.rstrip("/")
        self.headers = headers or {}
        self.timeout = timeout
        self.verify_ssl = verify_ssl
        self._client = httpx.AsyncClient(verify=self.verify_ssl)

    async def aclose(self):
        """Close the underlying async HTTP client."""
        await self._client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.aclose()

    def _build_url(self, endpoint: str) -> str:
        endpoint = endpoint.lstrip("/")
        return f"{self.base_url}/{endpoint}"

    async def request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Union[Dict[str, Any], List[Any]]] = None,
        headers: Optional[Dict[str, str]] = None,
        json_data: Optional[Union[Dict[str, Any], List[Any]]] = None,
        timeout: Optional[int] = None,
    ) -> Dict[str, Any]:
        url = self._build_url(endpoint)
        request_headers = {**self.headers}
        if headers:
            request_headers.update(headers)

        timeout = timeout or self.timeout

        try:
            response = await self._client.request(
                method=method.upper(),
                url=url,
                params=params,
                data=data,
                headers=request_headers,
                json=json_data,
                timeout=timeout,
            )
            return _handle_response(response)
        except httpx.TimeoutException:
            target = _safe_target(url)
            logger.error("Request timed out: {} {}", method, target)
            raise PaymentTimeoutError(f"Request timed out: {method} {target}")
        except httpx.ConnectError as exc:
            target = _safe_target(url)
            logger.error("Connection error to {}: {}", target, exc)
            raise ExternalServiceError(f"Connection error to {target}")
        except httpx.HTTPError as exc:
            target = _safe_target(url)
            logger.error("Request error to {} ({})", target, type(exc).__name__)
            raise ExternalServiceError(f"Request error to {target}")

    async def get(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None,
    ) -> Dict[str, Any]:
        return await self.request(
            method="GET",
            endpoint=endpoint,
            params=params,
            headers=headers,
            timeout=timeout,
        )

    async def post(
        self,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None,
    ) -> Dict[str, Any]:
        return await self.request(
            method="POST",
            endpoint=endpoint,
            data=data,
            json_data=json_data,
            params=params,
            headers=headers,
            timeout=timeout,
        )

    async def put(
        self,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None,
    ) -> Dict[str, Any]:
        return await self.request(
            method="PUT",
            endpoint=endpoint,
            data=data,
            json_data=json_data,
            params=params,
            headers=headers,
            timeout=timeout,
        )

    async def delete(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None,
    ) -> Dict[str, Any]:
        return await self.request(
            method="DELETE",
            endpoint=endpoint,
            params=params,
            headers=headers,
            timeout=timeout,
        )
