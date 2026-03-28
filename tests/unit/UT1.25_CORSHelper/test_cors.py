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

"""UT1.25: CORS Helper — CORS middleware configuration tests."""

from __future__ import annotations
import pytest
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport
from cloud_dog_api_kit.middleware.cors import configure_cors


@pytest.mark.asyncio
class TestCORSHelper:
    async def test_cors_configured_with_origins(self) -> None:
        app = FastAPI()
        configure_cors(app, allowed_origins=["http://localhost:3000"])

        @app.get("/test")
        async def test_ep():
            return {"ok": True}

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            r = await c.options(
                "/test",
                headers={
                    "Origin": "http://localhost:3000",
                    "Access-Control-Request-Method": "GET",
                },
            )
        assert r.status_code == 200

    async def test_cors_no_origins_blocks(self) -> None:
        app = FastAPI()
        configure_cors(app, allowed_origins=[])

        @app.get("/test")
        async def test_ep():
            return {"ok": True}

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            r = await c.options(
                "/test",
                headers={
                    "Origin": "http://evil.com",
                    "Access-Control-Request-Method": "GET",
                },
            )
        # No CORS header should be present for non-allowed origins
        assert "access-control-allow-origin" not in r.headers
