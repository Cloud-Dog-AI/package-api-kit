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

# cloud_dog_api_kit — Legacy route migration adapter
#
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Route migration adapter that maps legacy non-versioned paths to
#   versioned API paths and adds deprecation headers.
# Related requirements: FR18.4
# Related architecture: SA1

"""Legacy route migration helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from fastapi import FastAPI
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import RedirectResponse, Response


@dataclass(slots=True)
class LegacyRouteAdapter:
    """Adapter mapping legacy routes to versioned paths."""

    route_map: dict[str, str]
    sunset: str | None = None
    link: str | None = None
    redirect: bool = False
    deprecation: str = "true"
    methods: set[str] = field(default_factory=lambda: {"GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"})

    def resolve(self, path: str) -> str | None:
        """Resolve a legacy path to a versioned path."""
        return self.route_map.get(path)

    def deprecation_headers(self) -> dict[str, str]:
        """Build response headers for legacy route responses."""
        headers = {"Deprecation": self.deprecation}
        if self.sunset:
            headers["Sunset"] = self.sunset
        if self.link:
            headers["Link"] = self.link
        return headers

    def register(self, app: FastAPI) -> None:
        """Register legacy route adapter middleware on an app."""
        app.add_middleware(LegacyRouteAdapterMiddleware, adapter=self)


class LegacyRouteAdapterMiddleware(BaseHTTPMiddleware):
    """Middleware implementing legacy route mapping and deprecation headers."""

    def __init__(self, app: Any, adapter: LegacyRouteAdapter) -> None:
        super().__init__(app)
        self._adapter = adapter

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Map legacy route to versioned path and add deprecation headers."""
        target_path = self._adapter.resolve(request.url.path)
        if target_path is None or request.method.upper() not in self._adapter.methods:
            return await call_next(request)

        headers = self._adapter.deprecation_headers()
        if self._adapter.redirect:
            query = request.url.query
            location = target_path if not query else f"{target_path}?{query}"
            return RedirectResponse(url=location, status_code=307, headers=headers)

        request.scope["path"] = target_path
        request.scope["raw_path"] = target_path.encode("utf-8")
        response = await call_next(request)
        for name, value in headers.items():
            response.headers[name] = value
        return response
