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

"""UT1.29: Idempotency Store — in-memory store tests."""

from __future__ import annotations
import pytest
from cloud_dog_api_kit.idempotency.store import InMemoryIdempotencyStore


@pytest.mark.asyncio
class TestIdempotencyStore:
    async def test_set_and_get(self) -> None:
        store = InMemoryIdempotencyStore()
        await store.set("k1", {"status": 200, "body": {"ok": True}}, ttl=60)
        result = await store.get("k1")
        assert result is not None
        assert result["body"]["ok"] is True

    async def test_missing_key_returns_none(self) -> None:
        store = InMemoryIdempotencyStore()
        assert await store.get("nonexistent") is None

    async def test_expired_key_returns_none(self) -> None:
        store = InMemoryIdempotencyStore()
        await store.set("k2", {"data": "x"}, ttl=0)
        # TTL=0 means immediate expiry (monotonic + 0 < monotonic now)
        import asyncio

        await asyncio.sleep(0.01)
        assert await store.get("k2") is None

    async def test_clear(self) -> None:
        store = InMemoryIdempotencyStore()
        await store.set("k3", {"data": "y"}, ttl=60)
        store.clear()
        assert await store.get("k3") is None
