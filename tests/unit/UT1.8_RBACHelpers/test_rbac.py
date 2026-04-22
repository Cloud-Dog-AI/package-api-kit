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

"""UT1.8: RBAC Helpers — role and permission checks."""

from __future__ import annotations
import pytest
from fastapi import FastAPI, Depends, Request
from httpx import AsyncClient, ASGITransport
from cloud_dog_api_kit.auth.rbac import require_permission, require_admin
from cloud_dog_api_kit.errors import register_error_handlers
from starlette.middleware.base import BaseHTTPMiddleware


class _FakeAuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, roles=None, permissions=None):
        super().__init__(app)
        self._roles = roles or []
        self._permissions = permissions or []

    async def dispatch(self, request: Request, call_next):
        request.state.roles = self._roles
        request.state.permissions = self._permissions
        request.state.request_id = ""
        request.state.correlation_id = None
        return await call_next(request)


@pytest.mark.asyncio
class TestRBACHelpers:
    async def test_require_permission_granted(self) -> None:
        app = FastAPI()
        register_error_handlers(app)
        app.add_middleware(_FakeAuthMiddleware, roles=["editor"])

        @app.get("/edit", dependencies=[Depends(require_permission("editor"))])
        async def edit():
            return {"ok": True}

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            r = await c.get("/edit")
        assert r.status_code == 200

    async def test_require_permission_denied(self) -> None:
        app = FastAPI()
        register_error_handlers(app)
        app.add_middleware(_FakeAuthMiddleware, roles=["reader"])

        @app.get("/edit", dependencies=[Depends(require_permission("editor"))])
        async def edit():
            return {"ok": True}

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            r = await c.get("/edit")
        assert r.status_code == 403

    async def test_require_admin_granted(self) -> None:
        app = FastAPI()
        register_error_handlers(app)
        app.add_middleware(_FakeAuthMiddleware, roles=["admin"])

        @app.get("/admin", dependencies=[Depends(require_admin())])
        async def admin_ep():
            return {"ok": True}

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            r = await c.get("/admin")
        assert r.status_code == 200

    async def test_require_admin_denied(self) -> None:
        app = FastAPI()
        register_error_handlers(app)
        app.add_middleware(_FakeAuthMiddleware, roles=["reader"])

        @app.get("/admin", dependencies=[Depends(require_admin())])
        async def admin_ep():
            return {"ok": True}

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            r = await c.get("/admin")
        assert r.status_code == 403
        assert r.json()["error"]["code"] == "UNAUTHORISED"
