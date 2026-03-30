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

# cloud_dog_api_kit — MCP session lifecycle
#
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Lightweight in-memory MCP session manager with create/resume/
#   delete semantics for Mcp-Session-Id handling.
# Related requirements: FR18.5
# Related architecture: SA1

"""MCP session lifecycle support."""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable

SESSION_HEADER = "Mcp-Session-Id"


@dataclass(slots=True)
class McpSession:
    """In-memory MCP session state."""

    session_id: str
    created_at: float
    last_seen_at: float
    metadata: dict[str, Any] = field(default_factory=dict)


class McpSessionManager:
    """Manage in-memory MCP sessions.

    Related tests: UT1.41_MCPSessionLifecycle
    """

    def __init__(self, clock: Callable[[], float] | None = None) -> None:
        self._clock = clock or time.time
        self._lock = threading.Lock()
        self._sessions: dict[str, McpSession] = {}

    def create(self) -> McpSession:
        """Create a new session."""
        now = self._clock()
        session = McpSession(session_id=uuid.uuid4().hex, created_at=now, last_seen_at=now)
        with self._lock:
            self._sessions[session.session_id] = session
        return session

    def resume(self, session_id: str) -> McpSession | None:
        """Resume an existing session by ID."""
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return None
            session.last_seen_at = self._clock()
            return session

    def ensure(self, session_id: str | None) -> tuple[McpSession, bool]:
        """Get an existing session or create a new one.

        Returns:
            Tuple of (session, created_new).
        """
        if session_id:
            resumed = self.resume(session_id)
            if resumed is not None:
                return resumed, False
        created = self.create()
        return created, True

    def delete(self, session_id: str) -> bool:
        """Delete a session by ID."""
        with self._lock:
            return self._sessions.pop(session_id, None) is not None

    def exists(self, session_id: str) -> bool:
        """Check if a session exists."""
        with self._lock:
            return session_id in self._sessions
