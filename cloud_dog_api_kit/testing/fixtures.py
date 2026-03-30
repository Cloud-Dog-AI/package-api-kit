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

# cloud_dog_api_kit — Reusable test fixtures
#
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Reusable test fixtures for API testing — configured TestClient
#   with auth headers and database session protocol.
# Related requirements: FR16.1
# Related architecture: CC1.19

"""Reusable test fixtures for cloud_dog_api_kit."""

from __future__ import annotations


from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient


def create_test_client(
    app: FastAPI,
    base_url: str = "http://test",
    api_key: str | None = None,
    bearer_token: str | None = None,
) -> AsyncClient:
    """Create a configured async test client for a FastAPI application.

    Args:
        app: The FastAPI application.
        base_url: Base URL for the test client.
        api_key: Optional API key to include in all requests.
        bearer_token: Optional Bearer token to include in all requests.

    Returns:
        A configured httpx.AsyncClient.

    Related tests: UT1.34_TestFixtures
    """
    headers: dict[str, str] = {}
    if api_key:
        headers["X-API-Key"] = api_key
    if bearer_token:
        headers["Authorization"] = f"Bearer {bearer_token}"

    transport = ASGITransport(app=app)
    return AsyncClient(
        transport=transport,
        base_url=base_url,
        headers=headers,
    )


def create_auth_headers(
    api_key: str | None = None,
    bearer_token: str | None = None,
    app_id: str | None = None,
) -> dict[str, str]:
    """Create standard authentication headers.

    Args:
        api_key: API key value.
        bearer_token: Bearer token value.
        app_id: Application ID for service-to-service calls.

    Returns:
        A dictionary of HTTP headers.

    Related tests: UT1.34_TestFixtures
    """
    headers: dict[str, str] = {}
    if api_key:
        headers["X-API-Key"] = api_key
    if bearer_token:
        headers["Authorization"] = f"Bearer {bearer_token}"
    if app_id:
        headers["X-App-Id"] = app_id
    return headers
