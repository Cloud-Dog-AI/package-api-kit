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

"""UT1.17: Health Router — health/ready/live/status endpoint tests."""

from __future__ import annotations
import pytest
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport
from cloud_dog_api_kit.routers.health import create_health_router


@pytest.mark.asyncio
class TestHealthRouter:
    async def test_health_returns_ok(self) -> None:
        app = FastAPI()
        app.include_router(create_health_router("test-app", version="1.0.0"))
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            r = await c.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"
        assert r.json()["application"] == "test-app"

    async def test_ready_returns_ok(self) -> None:
        app = FastAPI()
        app.include_router(create_health_router("test-app"))
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            r = await c.get("/ready")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

    async def test_live_returns_ok(self) -> None:
        app = FastAPI()
        app.include_router(create_health_router("test-app"))
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            r = await c.get("/live")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

    async def test_ready_with_checks(self) -> None:
        async def db_check():
            return {"status": "ok", "latency_ms": 5}

        app = FastAPI()
        app.include_router(create_health_router("test-app", checks={"db": db_check}))
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            r = await c.get("/ready")
        body = r.json()
        assert body["status"] == "ok"
        assert body["checks"]["db"]["status"] == "ok"

    async def test_ready_degraded_on_failure(self) -> None:
        async def bad_check():
            return {"status": "error", "message": "down"}

        app = FastAPI()
        app.include_router(create_health_router("test-app", checks={"svc": bad_check}))
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            r = await c.get("/ready")
        assert r.json()["status"] == "degraded"

    async def test_status_returns_full_info(self) -> None:
        app = FastAPI()
        app.include_router(create_health_router("test-app", version="2.0.0", env_file="env-IT"))
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            r = await c.get("/status")
        body = r.json()
        assert body["application"] == "test-app"
        assert body["version"] == "2.0.0"
        assert body["env_file"] == "env-IT"
