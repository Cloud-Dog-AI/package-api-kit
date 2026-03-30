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

# cloud_dog_api_kit — Request/response logging middleware
#
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Middleware that logs request/response details with header
#   redaction for sensitive values (Authorization, X-API-Key, Cookie).
# Related requirements: FR12.1, CS1.2, CS1.6
# Related architecture: CC1.13

"""Request/response logging middleware for cloud_dog_api_kit."""

from __future__ import annotations

import logging
import time
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

REDACTED_HEADERS = frozenset({"authorization", "x-api-key", "cookie"})

logger = logging.getLogger("cloud_dog_api_kit.request_logging")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Request/response logging middleware with header redaction.

    Logs: request_id, correlation_id, user/system identity, method, path,
    status code, duration (ms), client IP. Redacts sensitive headers.

    Args:
        app: The ASGI application.

    Related tests: UT1.26_RequestLogging, SEC1.5_SecretRedaction
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Log request and response details.

        Args:
            request: The incoming HTTP request.
            call_next: The next middleware or handler.

        Returns:
            The HTTP response.
        """
        request_id = getattr(request.state, "request_id", "")
        correlation_id = getattr(request.state, "correlation_id", None)
        user = getattr(request.state, "user", None)
        client_ip = request.client.host if request.client else "unknown"

        logger.info(
            "Request started",
            extra={
                "request_id": request_id,
                "correlation_id": correlation_id,
                "user": user,
                "method": request.method,
                "path": request.url.path,
                "client_ip": client_ip,
            },
        )

        start_time = time.monotonic()
        response = await call_next(request)
        duration_ms = round((time.monotonic() - start_time) * 1000, 2)

        logger.info(
            "Request completed",
            extra={
                "request_id": request_id,
                "correlation_id": correlation_id,
                "user": user,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
                "client_ip": client_ip,
            },
        )

        return response
