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

"""UT1.30: Version Header — X-API-Version response header tests."""

from __future__ import annotations
import pytest
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport
from cloud_dog_api_kit.versioning.header import VersionHeaderMiddleware


@pytest.mark.asyncio
class TestVersionHeader:
    async def test_version_header_added(self) -> None:
        app = FastAPI()
        app.add_middleware(VersionHeaderMiddleware, version="v1")

        @app.get("/test")
        async def test_ep():
            return {"ok": True}

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            r = await c.get("/test")
        assert r.headers.get("X-API-Version") == "v1"

    async def test_custom_version(self) -> None:
        app = FastAPI()
        app.add_middleware(VersionHeaderMiddleware, version="v2")

        @app.get("/test")
        async def test_ep():
            return {"ok": True}

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            r = await c.get("/test")
        assert r.headers.get("X-API-Version") == "v2"
