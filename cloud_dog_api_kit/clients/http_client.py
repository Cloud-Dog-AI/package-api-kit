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

# cloud_dog_api_kit — Configured HTTP client with retry and timeouts
#
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Standard HTTP client module for service-to-service calls with
#   configurable timeouts, retry policy with exponential backoff + jitter,
#   and automatic header propagation (X-Request-Id, X-App-Id, API key).
# Related requirements: FR9.1, FR9.2
# Related architecture: CC1.15

"""Configured HTTP client for service-to-service calls."""

from __future__ import annotations

from dataclasses import dataclass

import httpx

from cloud_dog_api_kit.correlation.context import get_request_id, get_app_id
from cloud_dog_api_kit.clients.retry import RetryPolicy, RetryTransport


@dataclass
class ClientTimeout:
    """HTTP client timeout configuration.

    Attributes:
        connect: Connection timeout in seconds.
        read: Read timeout in seconds.
        total: Total request timeout in seconds.

    Related tests: UT1.23_HTTPClient
    """

    connect: float = 5.0
    read: float = 30.0
    total: float = 60.0


def create_http_client(
    base_url: str | None = None,
    timeout: ClientTimeout | None = None,
    retry_policy: RetryPolicy | None = None,
    app_id: str | None = None,
    api_key: str | None = None,
) -> httpx.AsyncClient:
    """Create a configured async HTTP client for service-to-service calls.

    The client automatically propagates X-Request-Id and X-App-Id headers
    and attaches an API key if provided.

    Args:
        base_url: Base URL for all requests.
        timeout: Timeout configuration. Uses defaults if None.
        retry_policy: Retry policy. Uses defaults if None.
        app_id: Calling service application ID.
        api_key: API key for authentication.

    Returns:
        A configured httpx.AsyncClient.

    Related tests: UT1.23_HTTPClient, ST1.11_HTTPClientEndToEnd
    """
    ct = timeout or ClientTimeout()
    policy = retry_policy or RetryPolicy()

    httpx_timeout = httpx.Timeout(
        timeout=ct.total,
        connect=ct.connect,
        read=ct.read,
        pool=ct.total,
    )

    headers: dict[str, str] = {}
    if app_id:
        headers["X-App-Id"] = app_id
    if api_key:
        headers["X-API-Key"] = api_key

    return httpx.AsyncClient(
        base_url=base_url or "",
        timeout=httpx_timeout,
        headers=headers,
        transport=RetryTransport(policy=policy, transport=httpx.AsyncHTTPTransport()),
        event_hooks={
            "request": [_inject_correlation_headers],
        },
    )


async def _inject_correlation_headers(request: httpx.Request) -> None:
    """Event hook to inject correlation headers into outgoing requests.

    Args:
        request: The outgoing HTTP request.
    """
    try:
        request_id = get_request_id()
        request.headers["X-Request-Id"] = request_id
    except Exception:
        pass

    try:
        app_id = get_app_id()
        if app_id:
            request.headers["X-App-Id"] = app_id
    except Exception:
        pass


def create_retry_transport(policy: RetryPolicy, transport: httpx.AsyncBaseTransport) -> RetryTransport:
    """Create a retry transport wrapper for httpx."""
    return RetryTransport(policy=policy, transport=transport)
