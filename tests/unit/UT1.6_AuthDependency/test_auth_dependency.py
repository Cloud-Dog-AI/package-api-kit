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

"""UT1.6: Auth Dependency — API key and Bearer auth tests."""

from __future__ import annotations
import pytest
from fastapi import FastAPI, Depends
from httpx import AsyncClient, ASGITransport
from cloud_dog_api_kit.auth.dependency import create_auth_dependency
from cloud_dog_api_kit.errors import register_error_handlers
from cloud_dog_api_kit.correlation import CorrelationMiddleware


def _verify_key(key: str) -> dict | None:
    if key == "valid-key":
        return {"user_id": "u-1", "roles": ["reader"], "tenant_id": "t-1"}
    return None


def _create_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(CorrelationMiddleware)
    register_error_handlers(app)
    auth = create_auth_dependency(api_key_verify_fn=_verify_key)

    @app.get("/protected", dependencies=[Depends(auth)])
    async def protected():
        return {"ok": True}

    @app.get("/public")
    async def public():
        return {"ok": True}

    return app


@pytest.mark.asyncio
class TestAuthDependency:
    async def test_valid_api_key_passes(self) -> None:
        app = _create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            r = await c.get("/protected", headers={"X-API-Key": "valid-key"})
        assert r.status_code == 200

    async def test_invalid_api_key_rejected(self) -> None:
        app = _create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            r = await c.get("/protected", headers={"X-API-Key": "bad-key"})
        assert r.status_code == 401
        assert r.json()["error"]["code"] == "UNAUTHENTICATED"

    async def test_missing_credentials_rejected(self) -> None:
        app = _create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            r = await c.get("/protected")
        assert r.status_code == 401

    async def test_public_endpoint_no_auth(self) -> None:
        app = _create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            r = await c.get("/public")
        assert r.status_code == 200

    async def test_config_api_key(self) -> None:
        app = FastAPI()
        app.add_middleware(CorrelationMiddleware)
        register_error_handlers(app)
        auth = create_auth_dependency(config_api_key="static-key")

        @app.get("/p", dependencies=[Depends(auth)])
        async def p():
            return {"ok": True}

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            r = await c.get("/p", headers={"X-API-Key": "static-key"})
        assert r.status_code == 200
