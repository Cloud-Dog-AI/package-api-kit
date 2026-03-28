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

# cloud_dog_api_kit — Idempotency store protocol and in-memory implementation
#
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Pluggable idempotency store with in-memory default implementation.
# Related requirements: FR4.4
# Related architecture: CC1.16

"""Idempotency store protocol and in-memory implementation."""

from __future__ import annotations

import time
from typing import Protocol


class IdempotencyStore(Protocol):
    """Protocol for idempotency key storage backends.

    Related tests: UT1.29_IdempotencyStore
    """

    async def get(self, key: str) -> dict | None:
        """Get a cached response by idempotency key.

        Args:
            key: The idempotency key.

        Returns:
            The cached response dict, or None if not found or expired.
        """
        ...

    async def set(self, key: str, response: dict, ttl: int) -> None:
        """Store a response with the given idempotency key.

        Args:
            key: The idempotency key.
            response: The response dict to cache.
            ttl: Time-to-live in seconds.
        """
        ...


class InMemoryIdempotencyStore:
    """In-memory idempotency store for development and testing.

    Stores responses in a dictionary with TTL-based expiry.

    Related tests: UT1.29_IdempotencyStore
    """

    def __init__(self) -> None:
        self._store: dict[str, tuple[dict, float]] = {}

    async def get(self, key: str) -> dict | None:
        """Get a cached response, returning None if expired.

        Args:
            key: The idempotency key.

        Returns:
            The cached response dict or None.
        """
        entry = self._store.get(key)
        if entry is None:
            return None
        response, expiry = entry
        if time.monotonic() > expiry:
            del self._store[key]
            return None
        return response

    async def set(self, key: str, response: dict, ttl: int) -> None:
        """Store a response with TTL.

        Args:
            key: The idempotency key.
            response: The response dict.
            ttl: Time-to-live in seconds.
        """
        self._store[key] = (response, time.monotonic() + ttl)

    def clear(self) -> None:
        """Clear all stored entries."""
        self._store.clear()
