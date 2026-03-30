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

"""UT1.27: Timeout Middleware — request timeout enforcement tests."""

from __future__ import annotations
import asyncio
import pytest
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport
from cloud_dog_api_kit.middleware.timeout import TimeoutMiddleware
from cloud_dog_api_kit.correlation import CorrelationMiddleware


@pytest.mark.asyncio
class TestTimeoutMiddleware:
    async def test_fast_request_passes(self) -> None:
        app = FastAPI()
        app.add_middleware(TimeoutMiddleware, timeout_seconds=5.0)
        app.add_middleware(CorrelationMiddleware)

        @app.get("/fast")
        async def fast():
            return {"ok": True}

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            r = await c.get("/fast")
        assert r.status_code == 200

    async def test_slow_request_times_out(self) -> None:
        app = FastAPI()
        app.add_middleware(TimeoutMiddleware, timeout_seconds=0.1)
        app.add_middleware(CorrelationMiddleware)

        @app.get("/slow")
        async def slow():
            await asyncio.sleep(5)
            return {"ok": True}

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            r = await c.get("/slow")
        assert r.status_code == 504
        body = r.json()
        assert body["ok"] is False
        assert body["error"]["code"] == "TIMEOUT"
        assert body["error"]["retryable"] is True
