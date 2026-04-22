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

"""UT1.5: Error Handler — exception-to-envelope conversion tests."""

from __future__ import annotations
import pytest
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport
from cloud_dog_api_kit.errors.exceptions import NotFoundError
from cloud_dog_api_kit.errors import register_error_handlers
from cloud_dog_api_kit.correlation import CorrelationMiddleware


def _create_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(CorrelationMiddleware)
    register_error_handlers(app)

    @app.get("/not-found")
    async def nf():
        raise NotFoundError(message="Item not found")

    @app.get("/internal")
    async def internal():
        raise RuntimeError("Unhandled")

    @app.get("/ok")
    async def ok():
        return {"ok": True}

    return app


@pytest.mark.asyncio
class TestErrorHandler:
    async def test_api_error_returns_envelope(self) -> None:
        app = _create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            r = await c.get("/not-found")
        assert r.status_code == 404
        body = r.json()
        assert body["ok"] is False
        assert body["error"]["code"] == "NOT_FOUND"

    async def test_unhandled_returns_500_envelope(self) -> None:
        app = _create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            r = await c.get("/internal")
        assert r.status_code == 500
        body = r.json()
        assert body["ok"] is False
        assert body["error"]["code"] == "INTERNAL_ERROR"

    async def test_no_stack_trace_in_error(self) -> None:
        app = _create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            r = await c.get("/internal")
        body = r.json()
        assert "Traceback" not in str(body)
        assert "RuntimeError" not in body["error"]["message"]

    async def test_success_not_affected(self) -> None:
        app = _create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            r = await c.get("/ok")
        assert r.status_code == 200
