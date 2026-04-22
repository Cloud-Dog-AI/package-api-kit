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

"""UT1.28: Idempotency Middleware — idempotency key handling tests."""

from __future__ import annotations
import pytest
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport
from cloud_dog_api_kit.idempotency.middleware import IdempotencyMiddleware
from cloud_dog_api_kit.correlation import CorrelationMiddleware

_call_count = 0


def _create_app() -> FastAPI:
    global _call_count
    _call_count = 0
    app = FastAPI()
    app.add_middleware(IdempotencyMiddleware, ttl_seconds=60)
    app.add_middleware(CorrelationMiddleware)

    @app.post("/create")
    async def create():
        global _call_count
        _call_count += 1
        return {"id": f"item-{_call_count}"}

    @app.get("/read")
    async def read():
        return {"ok": True}

    return app


@pytest.mark.asyncio
class TestIdempotencyMiddleware:
    async def test_first_request_executes(self) -> None:
        global _call_count
        app = _create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            r = await c.post("/create", json={}, headers={"Idempotency-Key": "k1"})
        assert r.status_code == 200
        assert r.json()["id"] == "item-1"

    async def test_duplicate_returns_cached(self) -> None:
        global _call_count
        app = _create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            r1 = await c.post("/create", json={}, headers={"Idempotency-Key": "k2"})
            r2 = await c.post("/create", json={}, headers={"Idempotency-Key": "k2"})
        assert r1.json() == r2.json()

    async def test_no_key_executes_normally(self) -> None:
        global _call_count
        app = _create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            r1 = await c.post("/create", json={})
            r2 = await c.post("/create", json={})
        assert r1.json()["id"] != r2.json()["id"]

    async def test_get_requests_bypass(self) -> None:
        app = _create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            r = await c.get("/read", headers={"Idempotency-Key": "k3"})
        assert r.status_code == 200
