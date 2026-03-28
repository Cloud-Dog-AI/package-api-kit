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

"""UT1.40: Legacy route migration and deprecation header tests."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from cloud_dog_api_kit.compat.routes import LegacyRouteAdapter, LegacyRouteAdapterMiddleware


@pytest.mark.asyncio
class TestLegacyRouteAdapter:
    async def test_legacy_route_rewritten_with_deprecation_headers(self) -> None:
        app = FastAPI()
        adapter = LegacyRouteAdapter(
            route_map={"/query": "/api/v1/query"},
            sunset="Wed, 30 Jun 2027 00:00:00 GMT",
            link='</api/v1/query>; rel="successor-version"',
        )
        app.add_middleware(LegacyRouteAdapterMiddleware, adapter=adapter)

        @app.post("/api/v1/query")
        async def query_handler() -> dict:
            return {"result": "ok"}

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
            response = await client.post("/query")

        assert response.status_code == 200
        assert response.json()["result"] == "ok"
        assert response.headers["Deprecation"] == "true"
        assert response.headers["Sunset"] == "Wed, 30 Jun 2027 00:00:00 GMT"
        assert response.headers["Link"] == '</api/v1/query>; rel="successor-version"'

    async def test_redirect_mode(self) -> None:
        app = FastAPI()
        adapter = LegacyRouteAdapter(route_map={"/query": "/api/v1/query"}, redirect=True)
        app.add_middleware(LegacyRouteAdapterMiddleware, adapter=adapter)

        @app.post("/api/v1/query")
        async def query_handler() -> dict:
            return {"result": "ok"}

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t", follow_redirects=False) as client:
            response = await client.post("/query")

        assert response.status_code == 307
        assert response.headers["location"] == "/api/v1/query"
