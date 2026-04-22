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

"""UT1.18: Ready/Live Endpoints — alias endpoint tests."""

from __future__ import annotations
import pytest
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport
from cloud_dog_api_kit.routers.health import create_health_router


@pytest.mark.asyncio
class TestReadyLiveEndpoints:
    async def test_live_and_health_return_same_structure(self) -> None:
        app = FastAPI()
        app.include_router(create_health_router("test-app", version="1.0.0"))
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            h = await c.get("/health")
            live_resp = await c.get("/live")
        assert h.json()["status"] == live_resp.json()["status"]
        assert h.json()["application"] == live_resp.json()["application"]

    async def test_ready_includes_checks_key(self) -> None:
        app = FastAPI()
        app.include_router(create_health_router("test-app"))
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            r = await c.get("/ready")
        assert "checks" in r.json()
