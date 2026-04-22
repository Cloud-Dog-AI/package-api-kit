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

# cloud_dog_api_kit — Retry policy
#
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Retry policy with exponential backoff + jitter for HTTP clients.
# Related requirements: FR9.2
# Related architecture: SA1

"""Retry policy utilities for cloud_dog_api_kit."""

from __future__ import annotations

import asyncio
import random
from dataclasses import dataclass

import httpx


@dataclass
class RetryPolicy:
    """Retry policy for idempotent operations.

    Related tests: UT1.24_RetryPolicy
    """

    max_retries: int = 3
    backoff_base: float = 0.5
    backoff_max: float = 30.0
    jitter: bool = True
    retry_status_codes: tuple[int, ...] = (502, 503, 504)

    def get_delay(self, attempt: int) -> float:
        """Return delay."""
        delay = min(self.backoff_base * (2**attempt), self.backoff_max)
        if self.jitter:
            delay = delay * (0.5 + random.random() * 0.5)
        return delay


class RetryTransport(httpx.AsyncBaseTransport):
    """HTTP transport wrapper with retry logic."""

    def __init__(self, policy: RetryPolicy, transport: httpx.AsyncBaseTransport) -> None:
        self._policy = policy
        self._transport = transport

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        """Handle handle async request."""
        last_response: httpx.Response | None = None
        last_exc: Exception | None = None

        for attempt in range(self._policy.max_retries + 1):
            try:
                response = await self._transport.handle_async_request(request)
                if response.status_code not in self._policy.retry_status_codes:
                    return response
                last_response = response
            except (httpx.ConnectError, httpx.ReadTimeout) as exc:
                last_exc = exc

            if attempt < self._policy.max_retries:
                await asyncio.sleep(self._policy.get_delay(attempt))

        if last_response is not None:
            return last_response
        if last_exc is not None:
            raise last_exc
        raise httpx.ConnectError("All retry attempts exhausted")
