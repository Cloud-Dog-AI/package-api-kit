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

# cloud_dog_api_kit — Correlation ID ASGI middleware
#
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: ASGI middleware that extracts X-Request-Id, X-Correlation-Id,
#   X-App-Id, and X-Host-Id from request headers, stores them in contextvars,
#   and attaches X-Request-Id to response headers.
# Related requirements: FR5.1, FR3.2
# Related architecture: CC1.8

"""Correlation ID ASGI middleware for cloud_dog_api_kit."""

from __future__ import annotations

import logging
import uuid
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from cloud_dog_api_kit.correlation.context import (
    clear_context,
    set_app_id,
    set_correlation_id,
    set_host_id,
    set_request_id,
)

_logger = logging.getLogger("cloud_dog_api_kit.correlation")


class CorrelationMiddleware(BaseHTTPMiddleware):
    """ASGI middleware for correlation ID extraction and propagation.

    On each request:
    1. Extracts ``X-Request-Id`` (generates UUID if absent).
    2. Extracts ``X-Correlation-Id`` if provided, propagates unchanged.
    3. Extracts ``X-App-Id`` and ``X-Host-Id`` if provided.
    4. Stores all in contextvars for the duration of the request.
    5. Attaches ``X-Request-Id`` to response headers.
    6. Sets ``request.state.request_id`` and ``request.state.correlation_id``.

    Related tests: UT1.11_CorrelationContext, UT1.12_CorrelationMiddleware
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process the request and propagate correlation context.

        Args:
            request: The incoming HTTP request.
            call_next: The next middleware or handler.

        Returns:
            The HTTP response with X-Request-Id header attached.
        """
        # Extract or generate request ID
        request_id = request.headers.get("x-request-id", "").strip()
        if not request_id:
            request_id = uuid.uuid4().hex
        set_request_id(request_id)

        # Extract optional correlation headers
        correlation_id = request.headers.get("x-correlation-id", "").strip() or None
        if correlation_id:
            set_correlation_id(correlation_id)

        app_id = request.headers.get("x-app-id", "").strip() or None
        if app_id:
            set_app_id(app_id)

        host_id = request.headers.get("x-host-id", "").strip() or None
        if host_id:
            set_host_id(host_id)

        # Store on request.state for downstream handlers
        request.state.request_id = request_id
        request.state.correlation_id = correlation_id
        request.state.app_id = app_id
        request.state.host_id = host_id

        try:
            response = await call_next(request)
            response.headers["X-Request-Id"] = request_id
            if correlation_id:
                response.headers["X-Correlation-Id"] = correlation_id
            return response
        except Exception as exc:
            # Catch unhandled exceptions that escape FastAPI's exception handlers
            # when BaseHTTPMiddleware is in the stack. Return a safe 500 envelope.
            from cloud_dog_api_kit.errors.exceptions import APIError

            if isinstance(exc, APIError):
                body = {
                    "ok": False,
                    "error": {
                        "code": exc.code,
                        "message": exc.message,
                        "details": exc.details,
                        "retryable": exc.retryable,
                    },
                    "meta": {"request_id": request_id, "correlation_id": correlation_id},
                }
                return JSONResponse(status_code=exc.status_code, content=body)
            _logger.exception("Unhandled exception", extra={"request_id": request_id})
            body = {
                "ok": False,
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "An internal error occurred",
                    "details": None,
                    "retryable": False,
                },
                "meta": {"request_id": request_id, "correlation_id": correlation_id},
            }
            return JSONResponse(status_code=500, content=body)
        finally:
            clear_context()
