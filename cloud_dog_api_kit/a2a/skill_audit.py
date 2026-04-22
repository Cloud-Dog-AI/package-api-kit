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

"""A2A skill audit middleware for PS-50 compliance.

License: Apache 2.0
Ownership: Cloud-Dog, Viewdeck Engineering Limited
Description: Wraps A2A skill handlers with structured audit logging.
Requirements: PS-50.AUD2
Tasks: W28A-737
"""

from __future__ import annotations

import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Optional


def a2a_skill_audit_middleware(
    skill_name: str,
    handler: Callable,
    *,
    service: str,
    logger: Optional[logging.Logger] = None,
) -> Callable:
    """Wrap an A2A skill handler to emit audit log entries for every invocation.

    Args:
        skill_name: The name of the A2A skill being wrapped.
        handler: The original skill handler callable.
        service: The emitting service name (e.g. ``"file-mcp-server"``).
        logger: Optional logger instance. Falls back to stdlib logging.

    Returns:
        A wrapped handler that logs audit entries for each skill invocation.

    Audit record fields:
        - correlation_id
        - service
        - skill_name (which skill was invoked)
        - actor (requesting agent or user)
        - task_id (A2A task ID)
        - outcome ("success" | "error")
        - duration_ms
        - timestamp
        - error_detail (if outcome is "error")
    """
    log = logger or logging.getLogger(f"cloud_dog_api_kit.a2a.audit.{service}")

    def _wrapped(text: str, *, task_id: str = "", actor: str = "a2a-caller", **kwargs: Any) -> Any:
        correlation_id = task_id or str(uuid.uuid4().hex[:16])
        ts = datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
        t0 = time.monotonic()
        try:
            result = handler(text, **kwargs)
            duration_ms = round((time.monotonic() - t0) * 1000, 2)
            log.info(
                "a2a_skill_invocation",
                extra={
                    "event_type": "a2a_skill_invocation",
                    "correlation_id": correlation_id,
                    "service": service,
                    "skill_name": skill_name,
                    "actor": actor,
                    "task_id": task_id,
                    "outcome": "success",
                    "duration_ms": duration_ms,
                    "timestamp": ts,
                },
            )
            return result
        except Exception as exc:
            duration_ms = round((time.monotonic() - t0) * 1000, 2)
            log.warning(
                "a2a_skill_invocation",
                extra={
                    "event_type": "a2a_skill_invocation",
                    "correlation_id": correlation_id,
                    "service": service,
                    "skill_name": skill_name,
                    "actor": actor,
                    "task_id": task_id,
                    "outcome": "error",
                    "duration_ms": duration_ms,
                    "timestamp": ts,
                    "error_detail": str(exc),
                },
            )
            raise

    _wrapped.__name__ = handler.__name__ if hasattr(handler, "__name__") else skill_name
    _wrapped.__doc__ = handler.__doc__
    return _wrapped
