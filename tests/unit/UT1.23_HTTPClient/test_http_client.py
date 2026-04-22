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

"""UT1.23: HTTP Client — configured client creation tests."""

from __future__ import annotations
import pytest
from cloud_dog_api_kit.clients.http_client import create_http_client, ClientTimeout


class TestHTTPClient:
    @pytest.mark.asyncio
    async def test_creates_async_client(self) -> None:
        client = create_http_client(base_url="http://example.com")
        assert client is not None
        await client.aclose()

    @pytest.mark.asyncio
    async def test_custom_timeout(self) -> None:
        ct = ClientTimeout(connect=2.0, read=10.0, total=20.0)
        client = create_http_client(base_url="http://example.com", timeout=ct)
        assert client is not None
        await client.aclose()

    @pytest.mark.asyncio
    async def test_api_key_header_set(self) -> None:
        client = create_http_client(base_url="http://example.com", api_key="test-key")
        assert client.headers.get("X-API-Key") == "test-key"
        await client.aclose()

    @pytest.mark.asyncio
    async def test_app_id_header_set(self) -> None:
        client = create_http_client(base_url="http://example.com", app_id="my-svc")
        assert client.headers.get("X-App-Id") == "my-svc"
        await client.aclose()
