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

# cloud_dog_api_kit — Profile context middleware
#
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Middleware that resolves request profile context from headers,
#   path patterns, or query parameters and stores it in request.state.
# Related requirements: FR18.6
# Related architecture: SA1

"""Profile context resolution middleware."""

from __future__ import annotations

import re
from typing import Any, Callable, Pattern

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from cloud_dog_api_kit.envelopes.error import error_envelope

DEFAULT_PATH_PATTERNS = (
    re.compile(r"/profiles/(?P<profile>[A-Za-z0-9._-]+)"),
    re.compile(r"/profile/(?P<profile>[A-Za-z0-9._-]+)"),
)


class ProfileContextMiddleware(BaseHTTPMiddleware):
    """Resolve per-request profile context.

    Resolution order:
    1. Header (default: `X-Profile`)
    2. Path pattern match
    3. Query parameter (default: `profile`)
    4. Default profile
    """

    def __init__(
        self,
        app: Any,
        *,
        header_name: str = "X-Profile",
        query_param: str = "profile",
        default_profile: str | None = None,
        allowed_profiles: set[str] | None = None,
        path_patterns: tuple[Pattern[str], ...] | None = None,
    ) -> None:
        super().__init__(app)
        self._header_name = header_name
        self._query_param = query_param
        self._default_profile = default_profile
        self._allowed_profiles = allowed_profiles
        self._path_patterns = path_patterns or DEFAULT_PATH_PATTERNS

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Resolve profile context and validate allowed profile list."""
        profile = (
            request.headers.get(self._header_name)
            or self._profile_from_path(request.url.path)
            or request.query_params.get(self._query_param)
            or self._default_profile
        )

        if self._allowed_profiles is not None and profile and profile not in self._allowed_profiles:
            request_id = getattr(request.state, "request_id", "")
            correlation_id = getattr(request.state, "correlation_id", None)
            return JSONResponse(
                status_code=400,
                content=error_envelope(
                    code="INVALID_REQUEST",
                    message="Invalid profile",
                    details={"profile": profile},
                    request_id=request_id,
                    correlation_id=correlation_id,
                ),
            )

        request.state.profile = profile
        return await call_next(request)

    def _profile_from_path(self, path: str) -> str | None:
        """Extract profile identifier from known path patterns."""
        for pattern in self._path_patterns:
            match = pattern.search(path)
            if match:
                return match.group("profile")
        return None
