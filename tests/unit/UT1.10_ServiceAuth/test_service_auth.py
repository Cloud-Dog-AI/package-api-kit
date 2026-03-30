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

"""UT1.10: Service Auth — service-to-service authentication tests."""

from __future__ import annotations
import pytest
from fastapi import FastAPI, Depends
from httpx import AsyncClient, ASGITransport
from cloud_dog_api_kit.auth.dependency import create_auth_dependency
from cloud_dog_api_kit.errors import register_error_handlers
from cloud_dog_api_kit.correlation import CorrelationMiddleware


def _verify_svc(key: str) -> dict | None:
    if key == "svc-key-001":
        return {"user_id": "svc-expert-agent", "roles": ["service"], "tenant_id": None}
    return None


@pytest.mark.asyncio
class TestServiceAuth:
    async def test_service_api_key_accepted(self) -> None:
        app = FastAPI()
        app.add_middleware(CorrelationMiddleware)
        register_error_handlers(app)
        auth = create_auth_dependency(api_key_verify_fn=_verify_svc)

        @app.get("/svc", dependencies=[Depends(auth)])
        async def svc():
            return {"ok": True}

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            r = await c.get("/svc", headers={"X-API-Key": "svc-key-001"})
        assert r.status_code == 200

    async def test_service_bad_key_rejected(self) -> None:
        app = FastAPI()
        app.add_middleware(CorrelationMiddleware)
        register_error_handlers(app)
        auth = create_auth_dependency(api_key_verify_fn=_verify_svc)

        @app.get("/svc", dependencies=[Depends(auth)])
        async def svc():
            return {"ok": True}

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            r = await c.get("/svc", headers={"X-API-Key": "wrong"})
        assert r.status_code == 401
