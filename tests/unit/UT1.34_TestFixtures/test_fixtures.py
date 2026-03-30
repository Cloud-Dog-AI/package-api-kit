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

"""UT1.34: Test Fixtures — reusable test fixture tests."""

from __future__ import annotations
import pytest
from fastapi import FastAPI
from cloud_dog_api_kit.testing.fixtures import create_test_client, create_auth_headers


class TestTestFixtures:
    # Async tests use httpx.AsyncClient with ASGITransport.
    # Keep sync tests unmarked to avoid pytest asyncio warnings.

    @pytest.mark.asyncio
    async def test_create_test_client(self) -> None:
        app = FastAPI()

        @app.get("/test")
        async def t():
            return {"ok": True}

        async with create_test_client(app) as c:
            r = await c.get("/test")
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_client_with_api_key(self) -> None:
        app = FastAPI()

        @app.get("/test")
        async def t():
            return {"ok": True}

        async with create_test_client(app, api_key="my-key") as c:
            assert c.headers.get("X-API-Key") == "my-key"

    @pytest.mark.asyncio
    async def test_client_with_bearer(self) -> None:
        app = FastAPI()

        @app.get("/test")
        async def t():
            return {"ok": True}

        async with create_test_client(app, bearer_token="tok") as c:
            assert c.headers.get("Authorization") == "Bearer tok"

    def test_create_auth_headers_api_key(self) -> None:
        h = create_auth_headers(api_key="k1")
        assert h == {"X-API-Key": "k1"}

    def test_create_auth_headers_bearer(self) -> None:
        h = create_auth_headers(bearer_token="t1")
        assert h == {"Authorization": "Bearer t1"}

    def test_create_auth_headers_combined(self) -> None:
        h = create_auth_headers(api_key="k", bearer_token="t", app_id="a")
        assert h["X-API-Key"] == "k"
        assert h["Authorization"] == "Bearer t"
        assert h["X-App-Id"] == "a"
