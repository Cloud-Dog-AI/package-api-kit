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

"""UT1.44: Request body size enforcement with HTTP 413 responses."""

from __future__ import annotations

import pytest
from fastapi import FastAPI, Request
from httpx import ASGITransport, AsyncClient

from cloud_dog_api_kit.middleware import RequestSizeLimitMiddleware


@pytest.mark.asyncio
class TestRequestSizeLimit:
    async def test_request_within_limit_passes(self) -> None:
        app = FastAPI()
        app.add_middleware(RequestSizeLimitMiddleware, max_bytes=16)

        @app.post("/upload")
        async def upload(request: Request) -> dict:
            body = await request.body()
            return {"size": len(body)}

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
            response = await client.post("/upload", content=b"small")

        assert response.status_code == 200
        assert response.json()["size"] == 5

    async def test_request_exceeding_limit_returns_413(self) -> None:
        app = FastAPI()
        app.add_middleware(RequestSizeLimitMiddleware, max_bytes=8)

        @app.post("/upload")
        async def upload() -> dict:
            return {"ok": True}

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
            response = await client.post("/upload", content=b"this payload is too large")

        assert response.status_code == 413
        body = response.json()
        assert body["ok"] is False
        assert body["error"]["code"] == "INVALID_REQUEST"
