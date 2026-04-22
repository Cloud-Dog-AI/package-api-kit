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

# cloud_dog_api_kit — Legacy envelope compatibility middleware
#
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Middleware to wrap legacy non-enveloped responses into standard
#   success/error envelopes during phased migrations.
# Related requirements: FR18.3
# Related architecture: SA1

"""Legacy response envelope compatibility middleware."""

from __future__ import annotations

import json
from typing import Any, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from cloud_dog_api_kit.envelopes import error_envelope, success_envelope


def legacy_envelope_route(func: Callable) -> Callable:
    """Mark a route endpoint as legacy-envelope compatible."""
    setattr(func, "__legacy_envelope__", True)
    return func


class LegacyEnvelopeMiddleware(BaseHTTPMiddleware):
    """Wrap legacy responses in standard envelopes for opt-in routes.

    Args:
        app: ASGI app.
        opt_in_paths: Exact route paths that require envelope wrapping.
        opt_in_header: Optional request header to force legacy envelope mode.
    """

    def __init__(
        self,
        app: Any,
        *,
        opt_in_paths: set[str] | None = None,
        opt_in_header: str = "X-Legacy-Envelope",
    ) -> None:
        super().__init__(app)
        self._opt_in_paths = set(opt_in_paths or set())
        self._opt_in_header = opt_in_header.lower()

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Apply compatibility envelopes on opt-in routes."""
        response = await call_next(request)
        if not self._should_wrap(request):
            return response
        if response.status_code == 204:
            return response

        body_bytes = b""
        async for chunk in response.body_iterator:
            body_bytes += chunk

        payload: Any
        if body_bytes:
            try:
                payload = json.loads(body_bytes)
            except json.JSONDecodeError:
                payload = {"message": body_bytes.decode("utf-8", errors="replace")}
        else:
            payload = {}

        request_id = getattr(request.state, "request_id", "")
        correlation_id = getattr(request.state, "correlation_id", None)

        if isinstance(payload, dict) and "ok" in payload and ("data" in payload or "error" in payload):
            envelope = payload
        elif response.status_code >= 400:
            message = "Request failed"
            details = None
            if isinstance(payload, dict):
                message = str(payload.get("message", payload.get("error", message)))
                details = payload.get("details")
            envelope = error_envelope(
                code="INVALID_REQUEST" if response.status_code < 500 else "INTERNAL_ERROR",
                message=message,
                details=details,
                request_id=request_id,
                correlation_id=correlation_id,
            )
        else:
            envelope = success_envelope(
                data=payload,
                request_id=request_id,
                correlation_id=correlation_id,
            )

        headers = {k: v for k, v in response.headers.items() if k.lower() != "content-length"}
        return JSONResponse(status_code=response.status_code, content=envelope, headers=headers)

    def _should_wrap(self, request: Request) -> bool:
        """Determine whether current request should be wrapped."""
        endpoint = request.scope.get("endpoint")
        if endpoint is not None and bool(getattr(endpoint, "__legacy_envelope__", False)):
            return True
        if request.url.path in self._opt_in_paths:
            return True
        return request.headers.get(self._opt_in_header, "").strip().lower() in {"1", "true", "yes"}
