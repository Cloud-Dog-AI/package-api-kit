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

"""UT1.7: Bearer Auth — Bearer token authentication tests."""

from __future__ import annotations
import pytest
from fastapi import FastAPI, Depends
from httpx import AsyncClient, ASGITransport
from cloud_dog_api_kit.auth.dependency import create_auth_dependency
from cloud_dog_api_kit.errors import register_error_handlers
from cloud_dog_api_kit.correlation import CorrelationMiddleware


async def _verify_bearer(token: str) -> dict | None:
    if token == "valid-token":
        return {"user_id": "u-2", "roles": ["admin"], "tenant_id": "t-1"}
    return None


def _create_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(CorrelationMiddleware)
    register_error_handlers(app)
    auth = create_auth_dependency(bearer_verify_fn=_verify_bearer)

    @app.get("/secured", dependencies=[Depends(auth)])
    async def secured():
        return {"ok": True}

    return app


@pytest.mark.asyncio
class TestBearerAuth:
    async def test_valid_bearer_passes(self) -> None:
        app = _create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            r = await c.get("/secured", headers={"Authorization": "Bearer valid-token"})
        assert r.status_code == 200

    async def test_invalid_bearer_rejected(self) -> None:
        app = _create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            r = await c.get("/secured", headers={"Authorization": "Bearer bad-token"})
        assert r.status_code == 401

    async def test_empty_bearer_rejected(self) -> None:
        app = _create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            r = await c.get("/secured", headers={"Authorization": "Bearer "})
        assert r.status_code == 401

    async def test_missing_auth_rejected(self) -> None:
        app = _create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            r = await c.get("/secured")
        assert r.status_code == 401
