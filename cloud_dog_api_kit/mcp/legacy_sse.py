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

# cloud_dog_api_kit — MCP legacy SSE server helpers
#
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Legacy SSE server-side transport helpers for `/sse` + `/message`
#   compatibility routes.
# Related requirements: FR18.1
# Related architecture: SA1

"""Legacy SSE server helpers for MCP compatibility routes."""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Any

from cloud_dog_api_kit.mcp.session import SESSION_HEADER


@dataclass
class LegacySSEConfig:
    """Configuration for server-side legacy SSE MCP compatibility routes.

    The dataclass also keeps the common client-side fields so
    `from cloud_dog_api_kit.mcp import LegacySSEConfig` remains useful for code
    that pairs the root import with `LegacySSETransport`.
    """

    base_url: str = ""
    sse_path: str = "/sse"
    message_path: str = "/message"
    messages_path: str = "/message"
    session_header: str = SESSION_HEADER
    api_key_header: str | None = None
    api_key: str | None = None
    accept_header: str | None = None
    auth_bearer_token: str | None = None
    protocol_version: str | None = None
    timeout_seconds: float = 30.0
    verify_tls: bool = True

    def __post_init__(self) -> None:
        self.sse_path = _normalise_path(self.sse_path, "/sse")
        self.message_path = _normalise_path(self.message_path or self.messages_path, "/message")
        self.messages_path = _normalise_path(self.messages_path or self.message_path, "/message")
        self.session_header = str(self.session_header or SESSION_HEADER).strip() or SESSION_HEADER


def _normalise_path(value: str | None, default: str) -> str:
    raw = str(value or "").strip() or default
    if not raw.startswith("/"):
        return f"/{raw}"
    return raw


class LegacySSEBroker:
    """Queue-backed broker for legacy SSE bootstrap and message delivery."""

    def __init__(self, config: LegacySSEConfig) -> None:
        self._config = config
        self._queues: dict[str, asyncio.Queue[dict[str, Any]]] = {}
        self._lock = asyncio.Lock()

    async def open_session(self, session_id: str) -> asyncio.Queue[dict[str, Any]]:
        """Create or reuse the queue for a legacy SSE session."""
        async with self._lock:
            queue = self._queues.get(session_id)
            if queue is None:
                queue = asyncio.Queue()
                self._queues[session_id] = queue
            return queue

    async def push(self, session_id: str, payload: dict[str, Any]) -> bool:
        """Push a JSON payload to an active legacy SSE stream."""
        async with self._lock:
            queue = self._queues.get(session_id)
        if queue is None:
            return False
        await queue.put(dict(payload))
        return True

    async def close_session(self, session_id: str) -> None:
        """Remove a legacy SSE session queue."""
        async with self._lock:
            self._queues.pop(session_id, None)

    def bootstrap_payload(self, session_id: str) -> dict[str, Any]:
        """Build the bootstrap payload sent on first SSE connect."""
        endpoint = f"{self._config.message_path}?session_id={session_id}&sessionId={session_id}"
        return {
            "endpoint": endpoint,
            "path": endpoint,
            "messages_path": self._config.message_path,
            "session_id": session_id,
            "sessionId": session_id,
        }

    async def event_stream(self, request: Any, session_id: str) -> Any:
        """Yield the bootstrap event and subsequent message events."""
        queue = await self.open_session(session_id)
        bootstrap = self.bootstrap_payload(session_id)
        yield f"event: endpoint\ndata: {json.dumps(bootstrap, ensure_ascii=True)}\n\n"
        try:
            while True:
                if hasattr(request, "is_disconnected") and await request.is_disconnected():
                    break
                try:
                    payload = await asyncio.wait_for(queue.get(), timeout=0.25)
                except asyncio.TimeoutError:
                    continue
                yield f"event: message\ndata: {json.dumps(payload, ensure_ascii=True)}\n\n"
        finally:
            await self.close_session(session_id)
