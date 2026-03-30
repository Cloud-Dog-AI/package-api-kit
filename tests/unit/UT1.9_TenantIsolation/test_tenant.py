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

"""UT1.9: Tenant Isolation — tenant boundary enforcement tests."""

from __future__ import annotations
import pytest
from fastapi import FastAPI, Depends
from httpx import AsyncClient, ASGITransport
from cloud_dog_api_kit.auth.rbac import require_tenant
from cloud_dog_api_kit.errors import register_error_handlers
from starlette.middleware.base import BaseHTTPMiddleware


class _TenantMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, tenant_id="t-1"):
        super().__init__(app)
        self._tid = tenant_id

    async def dispatch(self, request, call_next):
        request.state.tenant_id = self._tid
        request.state.request_id = ""
        request.state.correlation_id = None
        return await call_next(request)


@pytest.mark.asyncio
class TestTenantIsolation:
    async def test_matching_tenant_allowed(self) -> None:
        app = FastAPI()
        register_error_handlers(app)
        app.add_middleware(_TenantMiddleware, tenant_id="t-1")

        @app.get("/data/{tenant_id}", dependencies=[Depends(require_tenant())])
        async def data(tenant_id: str):
            return {"ok": True}

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            r = await c.get("/data/t-1")
        assert r.status_code == 200

    async def test_mismatched_tenant_rejected(self) -> None:
        app = FastAPI()
        register_error_handlers(app)
        app.add_middleware(_TenantMiddleware, tenant_id="t-1")

        @app.get("/data/{tenant_id}", dependencies=[Depends(require_tenant())])
        async def data(tenant_id: str):
            return {"ok": True}

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            r = await c.get("/data/t-OTHER")
        assert r.status_code == 403

    async def test_no_tenant_context_passes(self) -> None:
        app = FastAPI()
        register_error_handlers(app)

        class _NoTenantMW(BaseHTTPMiddleware):
            async def dispatch(self, request, call_next):
                request.state.tenant_id = None
                request.state.request_id = ""
                request.state.correlation_id = None
                return await call_next(request)

        app.add_middleware(_NoTenantMW)

        @app.get("/data/{tenant_id}", dependencies=[Depends(require_tenant())])
        async def data(tenant_id: str):
            return {"ok": True}

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            r = await c.get("/data/any-tenant")
        assert r.status_code == 200
