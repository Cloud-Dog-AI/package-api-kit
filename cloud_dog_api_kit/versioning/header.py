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

# cloud_dog_api_kit — X-API-Version header middleware
#
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Adds an `X-API-Version` header to all responses.
# Related requirements: FR10.4
# Related architecture: SA1

"""API version header middleware."""

from __future__ import annotations

from typing import Any, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class VersionHeaderMiddleware(BaseHTTPMiddleware):
    """Middleware that adds X-API-Version header to all responses.

    Args:
        app: The ASGI application.
        version: The API version string. Defaults to ``v1``.

    Related tests: UT1.30_VersionHeader
    """

    def __init__(self, app: Any, version: str = "v1") -> None:
        super().__init__(app)
        self._version = version

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add X-API-Version header to the response."""
        response = await call_next(request)
        response.headers["X-API-Version"] = self._version
        return response
