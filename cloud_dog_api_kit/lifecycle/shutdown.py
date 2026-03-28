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

# cloud_dog_api_kit — Graceful shutdown management
#
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: In-flight request draining and signal-handler integration for
#   deterministic graceful shutdown.
# Related requirements: FR18.9
# Related architecture: SA1

"""Graceful shutdown support for cloud_dog_api_kit."""

from __future__ import annotations

import asyncio
import signal
import threading
from typing import Any, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from cloud_dog_api_kit.envelopes.error import error_envelope


class GracefulShutdownManager:
    """Track in-flight requests and coordinate graceful shutdown.

    Args:
        drain_timeout_seconds: Maximum wait time for in-flight requests.

    Related tests: UT1.45_GracefulShutdown, ST1.13_StartupLifecycleIntegration
    """

    def __init__(self, drain_timeout_seconds: float = 5.0) -> None:
        if drain_timeout_seconds < 0:
            raise ValueError("drain_timeout_seconds must be >= 0")
        self._drain_timeout_seconds = drain_timeout_seconds
        self._lock = threading.Lock()
        self._active_requests = 0
        self._shutting_down = False
        self._all_requests_drained = asyncio.Event()
        self._all_requests_drained.set()

    @property
    def active_requests(self) -> int:
        """Current number of active requests."""
        with self._lock:
            return self._active_requests

    @property
    def shutting_down(self) -> bool:
        """Whether shutdown has started."""
        with self._lock:
            return self._shutting_down

    def mark_request_started(self) -> bool:
        """Mark a request start.

        Returns:
            True when request is accepted, False when shutdown is active.
        """
        with self._lock:
            if self._shutting_down:
                return False
            self._active_requests += 1
            self._all_requests_drained.clear()
            return True

    def mark_request_finished(self) -> None:
        """Mark request completion."""
        with self._lock:
            if self._active_requests > 0:
                self._active_requests -= 1
            if self._active_requests == 0:
                self._all_requests_drained.set()

    def set_shutting_down(self) -> None:
        """Set shutdown flag to reject new requests."""
        with self._lock:
            self._shutting_down = True
            if self._active_requests == 0:
                self._all_requests_drained.set()

    async def drain(self) -> bool:
        """Wait for in-flight requests to drain.

        Returns:
            True if drained before timeout, otherwise False.
        """
        if self.active_requests == 0:
            return True
        try:
            await asyncio.wait_for(self._all_requests_drained.wait(), timeout=self._drain_timeout_seconds)
            return True
        except asyncio.TimeoutError:
            return False

    async def initiate_shutdown(self) -> bool:
        """Start shutdown and drain requests."""
        self.set_shutting_down()
        return await self.drain()


class ShutdownDrainMiddleware(BaseHTTPMiddleware):
    """Reject new requests during shutdown and track in-flight requests.

    Args:
        app: The ASGI application.
        manager: Shared graceful shutdown manager.
    """

    def __init__(self, app: Any, manager: GracefulShutdownManager) -> None:
        super().__init__(app)
        self._manager = manager

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Track active request and reject when shutting down."""
        if not self._manager.mark_request_started():
            request_id = getattr(request.state, "request_id", "")
            correlation_id = getattr(request.state, "correlation_id", None)
            return JSONResponse(
                status_code=503,
                content=error_envelope(
                    code="INTERNAL_ERROR",
                    message="Service is shutting down",
                    details=None,
                    retryable=True,
                    request_id=request_id,
                    correlation_id=correlation_id,
                ),
            )
        try:
            return await call_next(request)
        finally:
            self._manager.mark_request_finished()


def install_shutdown_signal_handlers(
    manager: GracefulShutdownManager,
    loop: asyncio.AbstractEventLoop | None = None,
) -> dict[int, bool]:
    """Attempt to install SIGTERM/SIGINT handlers for graceful shutdown.

    Returns:
        Mapping of signal number to whether installation succeeded.
    """
    try:
        active_loop = loop or asyncio.get_running_loop()
    except RuntimeError:
        return {signal.SIGTERM: False, signal.SIGINT: False}

    results: dict[int, bool] = {}

    def _schedule_shutdown() -> None:
        active_loop.create_task(manager.initiate_shutdown())

    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            active_loop.add_signal_handler(sig, _schedule_shutdown)
            results[sig] = True
        except (NotImplementedError, RuntimeError, ValueError):
            results[sig] = False
    return results
