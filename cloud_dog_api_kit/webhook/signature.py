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

# cloud_dog_api_kit — Webhook signature verification middleware
#
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: HMAC-SHA256 webhook verification with timestamp checks and
#   replay detection.
# Related requirements: FR18.7
# Related architecture: SA1

"""Webhook signature verification middleware."""

from __future__ import annotations

import hmac
import hashlib
import threading
import time
from typing import Any, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from cloud_dog_api_kit.envelopes.error import error_envelope


def compute_webhook_signature(secret: str, timestamp: int, body: bytes) -> str:
    """Compute HMAC-SHA256 signature for webhook validation."""
    payload = f"{timestamp}.".encode("utf-8") + body
    digest = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    return digest


class _ReplayCache:
    """TTL cache for replay detection."""

    def __init__(self, ttl_seconds: int, clock: Callable[[], float]) -> None:
        self._ttl_seconds = ttl_seconds
        self._clock = clock
        self._cache: dict[str, float] = {}
        self._lock = threading.Lock()

    def mark_once(self, key: str) -> bool:
        """Record signature key and return False if already seen."""
        now = self._clock()
        with self._lock:
            expired = [k for k, expires_at in self._cache.items() if expires_at <= now]
            for expired_key in expired:
                self._cache.pop(expired_key, None)
            if key in self._cache:
                return False
            self._cache[key] = now + self._ttl_seconds
            return True


class WebhookSignatureMiddleware(BaseHTTPMiddleware):
    """Validate webhook signatures and prevent replay attacks.

    Args:
        app: ASGI app.
        secret: Shared webhook secret.
        protected_paths: Optional exact paths requiring verification.
        signature_header: Header containing the signature.
        timestamp_header: Header containing request timestamp.
        tolerance_seconds: Max allowed skew for timestamp validation.
        replay_ttl_seconds: Replay cache retention duration.
        clock: Injectable clock for tests.
    """

    def __init__(
        self,
        app: Any,
        *,
        secret: str,
        protected_paths: set[str] | None = None,
        signature_header: str = "X-Signature",
        timestamp_header: str = "X-Timestamp",
        tolerance_seconds: int = 300,
        replay_ttl_seconds: int = 600,
        clock: Callable[[], float] | None = None,
    ) -> None:
        super().__init__(app)
        self._secret = secret
        self._protected_paths = protected_paths
        self._signature_header = signature_header
        self._timestamp_header = timestamp_header
        self._tolerance_seconds = tolerance_seconds
        self._clock = clock or time.time
        self._replay_cache = _ReplayCache(ttl_seconds=replay_ttl_seconds, clock=self._clock)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Verify signature/timestamp/replay for protected routes."""
        if self._protected_paths is not None and request.url.path not in self._protected_paths:
            return await call_next(request)

        signature = request.headers.get(self._signature_header, "")
        timestamp_raw = request.headers.get(self._timestamp_header, "")
        if not signature or not timestamp_raw:
            return self._unauthorised_response(request, "Missing webhook signature headers")

        try:
            timestamp = int(timestamp_raw)
        except ValueError:
            return self._unauthorised_response(request, "Invalid webhook timestamp")

        now = int(self._clock())
        if abs(now - timestamp) > self._tolerance_seconds:
            return self._unauthorised_response(request, "Expired webhook timestamp")

        body = await request.body()
        provided = signature.removeprefix("sha256=").strip()
        expected = compute_webhook_signature(self._secret, timestamp, body)
        if not hmac.compare_digest(provided, expected):
            return self._unauthorised_response(request, "Invalid webhook signature")

        replay_key = f"{timestamp}:{provided}"
        if not self._replay_cache.mark_once(replay_key):
            return self._unauthorised_response(request, "Replay detected")

        request.state.webhook_verified = True
        return await call_next(request)

    def _unauthorised_response(self, request: Request, message: str) -> JSONResponse:
        """Create a standard 401 envelope for webhook verification failures."""
        request_id = getattr(request.state, "request_id", "")
        correlation_id = getattr(request.state, "correlation_id", None)
        return JSONResponse(
            status_code=401,
            content=error_envelope(
                code="UNAUTHENTICATED",
                message=message,
                request_id=request_id,
                correlation_id=correlation_id,
            ),
        )
