# Copyright 2026 Cloud-Dog, Viewdeck Engineering Limited
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
WebApiProxy — Standard web→API proxy for Cloud-Dog services.

Licence: Apache 2.0
Ownership: Cloud-Dog, Viewdeck Engineering Limited
Description: Shared proxy class that all web servers use to forward
    requests to their API server. Replaces 9 bespoke implementations.
Related Requirements: FR9.1, FR9.2
Related Architecture: CC1.15
Related Tests: UT1.XX_WebApiProxy

Recent Changes (max 10):
- 2026-04-08: W28A-849 — Initial implementation.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Mapping

import httpx

logger = logging.getLogger(__name__)


@dataclass
class ProxyResponse:
    """Structured response from the proxy."""

    status_code: int
    data: Any = None
    error: str | None = None
    headers: dict[str, str] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        """True when status_code is in the 2xx–3xx range."""
        return 200 <= self.status_code < 400


class WebApiProxy:
    """Standard web→API proxy backed by httpx.

    Provides async methods (``get()``, ``post()``, etc.) and sync methods
    (``get_sync()``, ``post_sync()``, etc.) that auto-inject the API key
    and return structured ``ProxyResponse`` objects.

    Async usage::

        proxy = WebApiProxy(api_base_url="http://localhost:8083", api_key="abc")
        result = await proxy.get("/health")

    Sync usage (for mixed sync/async web servers)::

        result = proxy.get_sync("/health")

    From cloud_dog_config::

        proxy = WebApiProxy.from_config(config)
    """

    def __init__(
        self,
        api_base_url: str,
        api_key: str = "",
        api_key_header: str = "X-API-Key",
        verify_tls: bool = True,
        timeout: float = 60.0,
    ) -> None:
        self._base_url = api_base_url.rstrip("/")
        self._api_key = api_key
        self._api_key_header = api_key_header
        self._verify_tls = verify_tls
        self._timeout = timeout

    @classmethod
    def from_config(cls, config: Any) -> "WebApiProxy":
        """Create a proxy from a cloud_dog_config Config object.

        Reads:
            - ``web_server.api_base_url`` or ``api_server.base_url``
            - ``api_server.api_key`` or ``auth.admin_token``
            - ``api_server.api_key_header`` (default ``X-API-Key``)
            - ``web_server.verify_tls`` (default True)
            - ``web_server.proxy_timeout`` (default 60.0)
        """
        get = getattr(config, "get", lambda k, d=None: d)
        api_base_url = str(
            get("web_server.api_base_url")
            or get("api_server.base_url")
            or "http://localhost:8083"
        )
        api_key = str(get("api_server.api_key") or get("auth.admin_token") or "")
        api_key_header = str(get("api_server.api_key_header") or "X-API-Key")
        verify_tls = bool(get("web_server.verify_tls") if get("web_server.verify_tls") is not None else True)
        timeout = float(get("web_server.proxy_timeout") or 60.0)
        return cls(
            api_base_url=api_base_url,
            api_key=api_key,
            api_key_header=api_key_header,
            verify_tls=verify_tls,
            timeout=timeout,
        )

    def _build_headers(
        self, extra_headers: Mapping[str, str] | None = None
    ) -> dict[str, str]:
        """Build request headers with API key and optional extras."""
        headers: dict[str, str] = {}
        if self._api_key:
            headers[self._api_key_header] = self._api_key
        if extra_headers:
            headers.update(extra_headers)
        return headers

    async def request(
        self,
        method: str,
        path: str,
        *,
        json: Any = None,
        params: dict[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
        cookies: dict[str, str] | None = None,
    ) -> ProxyResponse:
        """Send a proxied request to the API server.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE, PATCH).
            path: API path (e.g. ``/users/123``).
            json: JSON body for POST/PUT/PATCH.
            params: Query parameters.
            headers: Additional headers to forward.
            cookies: Cookies to forward (for session-based auth proxying).

        Returns:
            ProxyResponse with status_code, data, and optional error.
        """
        url = f"{self._base_url}{path}"
        merged_headers = self._build_headers(headers)
        try:
            async with httpx.AsyncClient(
                verify=self._verify_tls,
                timeout=httpx.Timeout(self._timeout),
                cookies=cookies,
            ) as client:
                response = await client.request(
                    method=method,
                    url=url,
                    json=json,
                    params=params,
                    headers=merged_headers,
                )
            try:
                data = response.json()
            except Exception:
                data = response.text
            if response.status_code >= 400:
                return ProxyResponse(
                    status_code=response.status_code,
                    data=data,
                    error=f"API {method} {path} returned {response.status_code}",
                    headers=dict(response.headers),
                )
            return ProxyResponse(
                status_code=response.status_code,
                data=data,
                headers=dict(response.headers),
            )
        except httpx.TimeoutException:
            logger.warning("Proxy timeout: %s %s", method, url)
            return ProxyResponse(status_code=504, error=f"Proxy timeout: {method} {path}")
        except httpx.ConnectError as exc:
            logger.warning("Proxy connect error: %s %s — %s", method, url, exc)
            return ProxyResponse(status_code=502, error=f"API unreachable: {method} {path}")
        except Exception as exc:
            logger.error("Proxy error: %s %s — %s", method, url, exc, exc_info=True)
            return ProxyResponse(status_code=500, error=f"Proxy error: {exc}")

    async def get(self, path: str, **kwargs: Any) -> ProxyResponse:
        """GET request to the API server."""
        return await self.request("GET", path, **kwargs)

    async def post(self, path: str, **kwargs: Any) -> ProxyResponse:
        """POST request to the API server."""
        return await self.request("POST", path, **kwargs)

    async def put(self, path: str, **kwargs: Any) -> ProxyResponse:
        """PUT request to the API server."""
        return await self.request("PUT", path, **kwargs)

    async def delete(self, path: str, **kwargs: Any) -> ProxyResponse:
        """DELETE request to the API server."""
        return await self.request("DELETE", path, **kwargs)

    async def patch(self, path: str, **kwargs: Any) -> ProxyResponse:
        """PATCH request to the API server."""
        return await self.request("PATCH", path, **kwargs)
