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

"""UT1.39: Legacy envelope compatibility middleware behaviour."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from starlette.responses import JSONResponse

from cloud_dog_api_kit.compat import LegacyEnvelopeMiddleware
from cloud_dog_api_kit.correlation import CorrelationMiddleware


@pytest.mark.asyncio
class TestLegacyEnvelopeMiddleware:
    async def test_wraps_opt_in_success_route(self) -> None:
        app = FastAPI()
        app.add_middleware(LegacyEnvelopeMiddleware, opt_in_paths={"/legacy"})
        app.add_middleware(CorrelationMiddleware)

        @app.get("/legacy")
        async def legacy() -> dict:
            return {"value": 7}

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
            response = await client.get("/legacy")

        assert response.status_code == 200
        body = response.json()
        assert body["ok"] is True
        assert body["data"]["value"] == 7
        assert "meta" in body

    async def test_non_opt_in_route_unchanged(self) -> None:
        app = FastAPI()
        app.add_middleware(LegacyEnvelopeMiddleware, opt_in_paths={"/legacy"})
        app.add_middleware(CorrelationMiddleware)

        @app.get("/modern")
        async def modern() -> dict:
            return {"value": 9}

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
            response = await client.get("/modern")

        assert response.status_code == 200
        assert response.json() == {"value": 9}

    async def test_wraps_opt_in_error_route(self) -> None:
        app = FastAPI()
        app.add_middleware(LegacyEnvelopeMiddleware, opt_in_paths={"/legacy-error"})
        app.add_middleware(CorrelationMiddleware)

        @app.get("/legacy-error")
        async def legacy_error() -> JSONResponse:
            return JSONResponse(status_code=400, content={"message": "bad request"})

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
            response = await client.get("/legacy-error")

        assert response.status_code == 400
        body = response.json()
        assert body["ok"] is False
        assert body["error"]["code"] == "INVALID_REQUEST"
