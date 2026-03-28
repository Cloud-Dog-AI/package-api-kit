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

# cloud_dog_api_kit — Timing middleware
#
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Measures request duration and exposes it via response header.
# Related requirements: FR12.1
# Related architecture: SA1

"""Request timing middleware for cloud_dog_api_kit."""

from __future__ import annotations

import time
from typing import Any, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class TimingMiddleware(BaseHTTPMiddleware):
    """Measures request duration and sets response header.

    Adds `X-Response-Time-Ms` header and stores `request.state.duration_ms`.
    """

    def __init__(self, app: Any, header_name: str = "X-Response-Time-Ms") -> None:
        super().__init__(app)
        self._header_name = header_name

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Handle dispatch."""
        start = time.monotonic()
        response = await call_next(request)
        duration_ms = round((time.monotonic() - start) * 1000, 2)
        setattr(request.state, "duration_ms", duration_ms)
        response.headers[self._header_name] = str(duration_ms)
        return response
