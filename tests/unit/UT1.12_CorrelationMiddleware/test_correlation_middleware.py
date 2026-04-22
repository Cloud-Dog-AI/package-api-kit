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

"""UT1.12: Correlation Middleware — header extraction and propagation."""

from __future__ import annotations
import pytest
from fastapi import FastAPI, Request
from httpx import AsyncClient, ASGITransport
from cloud_dog_api_kit.correlation import CorrelationMiddleware


def _create_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(CorrelationMiddleware)

    @app.get("/echo")
    async def echo(request: Request):
        return {
            "request_id": request.state.request_id,
            "correlation_id": request.state.correlation_id,
            "app_id": request.state.app_id,
            "host_id": request.state.host_id,
        }

    return app


@pytest.mark.asyncio
class TestCorrelationMiddleware:
    async def test_generates_request_id_when_missing(self) -> None:
        app = _create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            r = await c.get("/echo")
        assert "X-Request-Id" in r.headers
        assert len(r.headers["X-Request-Id"]) == 32

    async def test_preserves_incoming_request_id(self) -> None:
        app = _create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            r = await c.get("/echo", headers={"X-Request-Id": "custom-req-id"})
        assert r.headers["X-Request-Id"] == "custom-req-id"
        assert r.json()["request_id"] == "custom-req-id"

    async def test_extracts_correlation_id(self) -> None:
        app = _create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            r = await c.get("/echo", headers={"X-Correlation-Id": "corr-abc"})
        assert r.json()["correlation_id"] == "corr-abc"
        assert r.headers.get("X-Correlation-Id") == "corr-abc"

    async def test_extracts_app_id(self) -> None:
        app = _create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            r = await c.get("/echo", headers={"X-App-Id": "expert-agent"})
        assert r.json()["app_id"] == "expert-agent"

    async def test_extracts_host_id(self) -> None:
        app = _create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            r = await c.get("/echo", headers={"X-Host-Id": "host-001"})
        assert r.json()["host_id"] == "host-001"

    async def test_sets_request_state(self) -> None:
        app = _create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            r = await c.get("/echo", headers={"X-Request-Id": "state-test"})
        data = r.json()
        assert data["request_id"] == "state-test"
