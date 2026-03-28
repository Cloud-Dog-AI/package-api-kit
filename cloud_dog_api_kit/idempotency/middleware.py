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

# cloud_dog_api_kit — Idempotency middleware
#
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: ASGI middleware that honours Idempotency-Key headers for
#   creation endpoints, caching and replaying responses.
# Related requirements: FR4.4
# Related architecture: CC1.16

"""Idempotency middleware for cloud_dog_api_kit."""

from __future__ import annotations

import json
from typing import Any, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from cloud_dog_api_kit.idempotency.store import InMemoryIdempotencyStore


class IdempotencyMiddleware(BaseHTTPMiddleware):
    """Middleware that honours Idempotency-Key headers.

    First request with a key executes normally and caches the response.
    Subsequent requests with the same key return the cached response.
    Expired keys re-execute. Missing keys pass through.

    Args:
        app: The ASGI application.
        store: Pluggable idempotency store. Defaults to in-memory.
        ttl_seconds: Time-to-live for cached responses. Defaults to 86400 (24h).

    Related tests: UT1.28_IdempotencyMiddleware, ST1.10_IdempotencyEndToEnd
    """

    def __init__(
        self,
        app: Any,
        store: Any | None = None,
        ttl_seconds: int = 86400,
    ) -> None:
        super().__init__(app)
        self._store = store or InMemoryIdempotencyStore()
        self._ttl = ttl_seconds

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with idempotency key support.

        Args:
            request: The incoming HTTP request.
            call_next: The next middleware or handler.

        Returns:
            The HTTP response (cached or fresh).
        """
        # Only apply to POST/PUT methods
        if request.method not in ("POST", "PUT"):
            return await call_next(request)

        idem_key = request.headers.get("idempotency-key", "").strip()
        if not idem_key:
            return await call_next(request)

        # Check cache
        cached = await self._store.get(idem_key)
        if cached is not None:
            return JSONResponse(
                status_code=cached.get("status_code", 200),
                content=cached.get("body"),
            )

        # Execute request
        response = await call_next(request)

        # Cache the response body
        if 200 <= response.status_code < 300:
            body_bytes = b""
            async for chunk in response.body_iterator:
                if isinstance(chunk, bytes):
                    body_bytes += chunk
                else:
                    body_bytes += chunk.encode("utf-8")

            try:
                body_json = json.loads(body_bytes)
            except (json.JSONDecodeError, ValueError):
                body_json = body_bytes.decode("utf-8")

            await self._store.set(
                idem_key,
                {"status_code": response.status_code, "body": body_json},
                self._ttl,
            )

            return JSONResponse(
                status_code=response.status_code,
                content=body_json,
                headers=dict(response.headers),
            )

        return response
