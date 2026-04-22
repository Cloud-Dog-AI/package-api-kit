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

# cloud_dog_api_kit — Request timeout middleware
#
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Configurable request timeout middleware that returns a standard
#   TIMEOUT error envelope when a request exceeds the configured duration.
# Related requirements: FR13.1
# Related architecture: CC1.13

"""Request timeout middleware for cloud_dog_api_kit."""

from __future__ import annotations

import asyncio
from typing import Any, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from cloud_dog_api_kit.envelopes.error import error_envelope


class TimeoutMiddleware(BaseHTTPMiddleware):
    """Request timeout middleware.

    Returns a standard TIMEOUT error envelope when a request exceeds
    the configured duration. Streaming endpoints should use jobs instead.

    Args:
        app: The ASGI application.
        timeout_seconds: Default request timeout in seconds. Defaults to 30.

    Related tests: UT1.27_TimeoutMiddleware
    """

    def __init__(self, app: Any, timeout_seconds: float = 30.0) -> None:
        super().__init__(app)
        self._timeout = timeout_seconds

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with timeout enforcement.

        Args:
            request: The incoming HTTP request.
            call_next: The next middleware or handler.

        Returns:
            The HTTP response or a TIMEOUT error envelope.
        """
        try:
            return await asyncio.wait_for(
                call_next(request),
                timeout=self._timeout,
            )
        except asyncio.TimeoutError:
            request_id = getattr(request.state, "request_id", "")
            body = error_envelope(
                code="TIMEOUT",
                message=f"Request timed out after {self._timeout}s",
                retryable=True,
                request_id=request_id,
            )
            return JSONResponse(status_code=504, content=body)
