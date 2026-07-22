"""Async WxCC API client.

Wraps ``httpx.AsyncClient`` to:
  * inject the per-session bearer token from the OAuth broker,
  * select the correct base URL for the API family (Config vs Reporting/Search),
  * retry ``429`` and ``5xx`` with exponential backoff + jitter, honoring
    ``Retry-After``,
  * map non-2xx responses to typed exceptions.

Tokens are resolved internally and never returned to callers or logged.
"""

from __future__ import annotations

import asyncio
import random
from typing import Any

import httpx

from ..auth.oauth import OAuthBroker
from ..config import ApiFamily, Settings, get_settings
from ..errors import (
    InsufficientPermissionsError,
    NotFoundError,
    RateLimitError,
    WxccApiError,
)
from ..logging_config import get_logger

logger = get_logger(__name__)

_RETRYABLE_STATUS = {500, 502, 503, 504}


class WxccApiClient:
    """Async client for the WxCC Config and Reporting/Search API families."""

    def __init__(
        self,
        broker: OAuthBroker,
        settings: Settings | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        """Initialize the client.

        Args:
            broker: OAuth token broker used to resolve per-session tokens.
            settings: Runtime settings; defaults to the cached global settings.
            http_client: Optional injected ``httpx.AsyncClient`` (used in tests).
        """
        self._broker = broker
        self._settings = settings or get_settings()
        self._http = http_client
        self._owns_http = http_client is None

    def _base_url(self, family: str) -> str:
        """Return the base URL for the given API family (Config only)."""
        if family == ApiFamily.CONFIG:
            return self._settings.config_api_base.rstrip("/")
        raise WxccApiError(f"Unknown API family: {family}", family=family)

    async def _client(self) -> httpx.AsyncClient:
        if self._http is None:
            self._http = httpx.AsyncClient(timeout=self._settings.http_timeout_seconds)
        return self._http

    async def aclose(self) -> None:
        """Close the underlying HTTP client if this instance owns it."""
        if self._owns_http and self._http is not None:
            await self._http.aclose()
            self._http = None

    async def put(
        self,
        family: str,
        path: str,
        session_id: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> Any:
        """Issue an authenticated PUT and return parsed JSON."""
        return await self._request(
            "PUT", family, path, session_id, params=params, json_body=json_body
        )

    async def patch(
        self,
        family: str,
        path: str,
        session_id: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> Any:
        """Issue an authenticated PATCH and return parsed JSON."""
        return await self._request(
            "PATCH", family, path, session_id, params=params, json_body=json_body
        )

    async def delete(
        self,
        family: str,
        path: str,
        session_id: str,
        *,
        params: dict[str, Any] | None = None,
    ) -> Any:
        """Issue an authenticated DELETE and return parsed JSON (or empty dict)."""
        return await self._request("DELETE", family, path, session_id, params=params)

    async def post(
        self,
        family: str,
        path: str,
        session_id: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> Any:
        """Issue an authenticated POST and return parsed JSON.

        Args:
            family: API family (``config`` or ``reporting``).
            path: Path relative to the family base URL.
            session_id: MCP session id used to resolve the bearer token.
            params: Optional query parameters.
            json_body: Optional JSON request body.

        Returns:
            The parsed JSON body.

        Raises:
            NotFoundError, InsufficientPermissionsError, RateLimitError,
            WxccApiError: Mapped from non-2xx responses.
        """
        return await self._request(
            "POST", family, path, session_id, params=params, json_body=json_body
        )

    async def get(
        self,
        family: str,
        path: str,
        session_id: str,
        *,
        params: dict[str, Any] | None = None,
    ) -> Any:
        """Issue an authenticated GET and return parsed JSON.

        Args:
            family: API family (``config`` or ``reporting``).
            path: Path relative to the family base URL (already formatted).
            session_id: MCP session id used to resolve the bearer token.
            params: Optional query parameters.

        Returns:
            The parsed JSON body.

        Raises:
            NotFoundError, InsufficientPermissionsError, RateLimitError,
            WxccApiError: Mapped from non-2xx responses.
        """
        return await self._request("GET", family, path, session_id, params=params)

    async def _request(
        self,
        method: str,
        family: str,
        path: str,
        session_id: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> Any:
        url = f"{self._base_url(family)}{path}"
        client = await self._client()
        max_attempts = max(1, self._settings.http_max_retries)

        last_exc: Exception | None = None
        for attempt in range(1, max_attempts + 1):
            token = await self._broker.get_valid_token(session_id)
            headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
            logger.info(
                "wxcc_api_call",
                method=method,
                family=family,
                path=path,
                attempt=attempt,
                # NB: headers intentionally omitted; redaction covers them anyway.
            )
            try:
                resp = await client.request(
                    method, url, headers=headers, params=params, json=json_body
                )
            except httpx.HTTPError as exc:
                last_exc = exc
                if attempt < max_attempts:
                    await self._sleep_backoff(attempt, None)
                    continue
                raise WxccApiError(
                    f"Network error calling WxCC {family} API.", family=family
                ) from exc

            if 200 <= resp.status_code < 300:
                if not resp.content:
                    return {}
                return resp.json()

            should_retry = self._handle_error_status(resp, family, attempt, max_attempts)
            if should_retry:
                await self._sleep_backoff(attempt, _retry_after_seconds(resp))
                continue
            # Non-retryable: map and raise.
            self._raise_for_status(resp, family)

        # Exhausted retries without a definitive mapped error.
        if last_exc is not None:  # pragma: no cover - defensive
            raise WxccApiError(f"WxCC {family} API call failed.", family=family) from last_exc
        raise WxccApiError(f"WxCC {family} API call failed after retries.", family=family)

    def _handle_error_status(
        self, resp: httpx.Response, family: str, attempt: int, max_attempts: int
    ) -> bool:
        """Return True if the response is retryable and attempts remain."""
        status = resp.status_code
        if status == 429 or status in _RETRYABLE_STATUS:
            if attempt < max_attempts:
                logger.warning("wxcc_api_retry", family=family, status=status, attempt=attempt)
                return True
        return False

    @staticmethod
    def _raise_for_status(resp: httpx.Response, family: str) -> None:
        """Map a non-2xx response to a typed exception and raise it."""
        status = resp.status_code
        detail = _safe_detail(resp)
        if status == 404:
            raise NotFoundError(
                "The requested resource was not found.",
                status_code=status,
                detail=detail,
                family=family,
            )
        if status == 403:
            raise InsufficientPermissionsError(
                "You do not have permission to perform this operation.",
                status_code=status,
                detail=detail,
                family=family,
            )
        if status == 429:
            raise RateLimitError(
                "Rate limit exceeded and retries were exhausted.",
                status_code=status,
                detail=detail,
                family=family,
                retry_after=_retry_after_seconds(resp),
            )
        raise WxccApiError(
            f"WxCC {family} API returned HTTP {status}.",
            status_code=status,
            detail=detail,
            family=family,
        )

    async def _sleep_backoff(self, attempt: int, retry_after: float | None) -> None:
        """Sleep using ``Retry-After`` if provided, else exponential backoff + jitter."""
        if retry_after is not None:
            await asyncio.sleep(retry_after)
            return
        base = min(2 ** (attempt - 1), 30)
        await asyncio.sleep(base + random.uniform(0, 0.5))


def _retry_after_seconds(resp: httpx.Response) -> float | None:
    """Parse the ``Retry-After`` header (seconds form) if present."""
    value = resp.headers.get("Retry-After")
    if value is None:
        return None
    try:
        return float(value)
    except ValueError:
        # HTTP-date form is not handled here; fall back to backoff.
        return None


def _safe_detail(resp: httpx.Response) -> str:
    """Extract a short, safe error detail without leaking sensitive data."""
    try:
        data = resp.json()
        if isinstance(data, dict):
            for key in ("message", "error_description", "error", "detail"):
                if key in data and isinstance(data[key], str):
                    return data[key]
    except (ValueError, TypeError):
        pass
    return f"HTTP {resp.status_code}"
