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

"""UT1.42: Profile context resolution from header/path/query/default."""

from __future__ import annotations

import pytest
from fastapi import FastAPI, Request
from httpx import ASGITransport, AsyncClient

from cloud_dog_api_kit.compat.profile import ProfileContextMiddleware


@pytest.mark.asyncio
class TestProfileContextMiddleware:
    async def test_header_path_query_resolution_order(self) -> None:
        app = FastAPI()
        app.add_middleware(ProfileContextMiddleware, default_profile="default")

        @app.get("/profiles/{profile}/echo")
        async def echo(request: Request, profile: str) -> dict:
            return {"profile": request.state.profile, "path_profile": profile}

        @app.get("/echo")
        async def echo_simple(request: Request) -> dict:
            return {"profile": request.state.profile}

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
            by_path = await client.get("/profiles/path-profile/echo")
            by_query = await client.get("/echo?profile=query-profile")
            by_header = await client.get(
                "/profiles/path-profile/echo?profile=query-profile", headers={"X-Profile": "hdr"}
            )
            by_default = await client.get("/echo")

        assert by_path.json()["profile"] == "path-profile"
        assert by_query.json()["profile"] == "query-profile"
        assert by_header.json()["profile"] == "hdr"
        assert by_default.json()["profile"] == "default"

    async def test_invalid_profile_rejected(self) -> None:
        app = FastAPI()
        app.add_middleware(ProfileContextMiddleware, allowed_profiles={"alpha", "beta"})

        @app.get("/echo")
        async def echo(request: Request) -> dict:
            return {"profile": request.state.profile}

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
            response = await client.get("/echo", headers={"X-Profile": "gamma"})

        assert response.status_code == 400
        assert response.json()["error"]["code"] == "INVALID_REQUEST"
