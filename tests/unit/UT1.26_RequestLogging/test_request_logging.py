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

"""UT1.26: Request Logging — request/response logging middleware tests."""

from __future__ import annotations
import pytest
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport
from cloud_dog_api_kit.middleware.logging import RequestLoggingMiddleware
from cloud_dog_api_kit.correlation import CorrelationMiddleware


@pytest.mark.asyncio
class TestRequestLogging:
    async def test_middleware_does_not_break_requests(self) -> None:
        app = FastAPI()
        app.add_middleware(RequestLoggingMiddleware)
        app.add_middleware(CorrelationMiddleware)

        @app.get("/test")
        async def test_ep():
            return {"ok": True}

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            r = await c.get("/test")
        assert r.status_code == 200
        assert r.json()["ok"] is True

    async def test_logging_preserves_response(self) -> None:
        app = FastAPI()
        app.add_middleware(RequestLoggingMiddleware)
        app.add_middleware(CorrelationMiddleware)

        @app.get("/data")
        async def data_ep():
            return {"items": [1, 2, 3]}

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            r = await c.get("/data")
        assert r.json()["items"] == [1, 2, 3]
