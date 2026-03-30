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

# cloud_dog_api_kit — Request size limit middleware
#
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Middleware that enforces a maximum request body size and
#   returns a standard envelope with HTTP 413 when exceeded.
# Related requirements: FR18.8
# Related architecture: SA1

"""Request body size limit middleware for cloud_dog_api_kit."""

from __future__ import annotations

from typing import Any, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from cloud_dog_api_kit.envelopes.error import error_envelope


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Enforce a maximum request body size.

    The middleware checks `Content-Length` when available and validates the
    effective byte size by reading the request body when needed.

    Args:
        app: The ASGI application.
        max_bytes: Maximum allowed body size in bytes.

    Related tests: UT1.44_RequestSizeLimit
    """

    def __init__(self, app: Any, max_bytes: int) -> None:
        if max_bytes < 1:
            raise ValueError("max_bytes must be >= 1")
        super().__init__(app)
        self._max_bytes = max_bytes

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Reject requests larger than the configured threshold."""
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                if int(content_length) > self._max_bytes:
                    return self._too_large_response(request)
            except ValueError:
                # Non-integer content length is treated as invalid request size.
                return self._too_large_response(request)

        body = await request.body()
        if len(body) > self._max_bytes:
            return self._too_large_response(request)
        return await call_next(request)

    def _too_large_response(self, request: Request) -> JSONResponse:
        """Build a standard 413 error response."""
        request_id = getattr(request.state, "request_id", "")
        correlation_id = getattr(request.state, "correlation_id", None)
        return JSONResponse(
            status_code=413,
            content=error_envelope(
                code="INVALID_REQUEST",
                message=f"Request body exceeds maximum size ({self._max_bytes} bytes)",
                details={"max_bytes": self._max_bytes},
                retryable=False,
                request_id=request_id,
                correlation_id=correlation_id,
            ),
        )
