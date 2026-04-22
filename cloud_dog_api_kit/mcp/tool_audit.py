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

"""MCP tool audit middleware for PS-50 compliance.

License: Apache 2.0
Ownership: Cloud-Dog, Viewdeck Engineering Limited
Description: Wraps MCP tool handlers with structured audit logging.
Requirements: PS-50.AUD1
Tasks: W28A-737
"""

from __future__ import annotations

import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Optional

_DEFAULT_REDACT_FIELDS = frozenset({
    "password", "secret", "token", "api_key", "credential", "auth",
    "access_token", "refresh_token", "key_hash",
})


def _redact_params(
    params: dict[str, Any],
    redact_fields: frozenset[str] = _DEFAULT_REDACT_FIELDS,
) -> dict[str, Any]:
    """Redact sensitive parameter values.

    Args:
        params: The raw parameter dict from the tool call.
        redact_fields: Field names whose values should be replaced.

    Returns:
        A copy of the dict with sensitive values replaced by ``[REDACTED]``.
    """
    cleaned: dict[str, Any] = {}
    for key, value in params.items():
        if key.lower() in redact_fields:
            cleaned[key] = "[REDACTED]"
        else:
            cleaned[key] = value
    return cleaned


def mcp_tool_audit_middleware(
    tool_name: str,
    handler: Callable,
    *,
    service: str,
    logger: Optional[logging.Logger] = None,
    redact_fields: Optional[frozenset[str]] = None,
) -> Callable:
    """Wrap an MCP tool handler to emit audit log entries for every tool call.

    Args:
        tool_name: The name of the MCP tool being wrapped.
        handler: The original tool handler callable.
        service: The emitting service name (e.g. ``"file-mcp-server"``).
        logger: Optional logger instance. Falls back to stdlib logging.
        redact_fields: Additional field names to redact from parameters.

    Returns:
        A wrapped handler that logs audit entries before and after execution.

    Audit record fields:
        - correlation_id (from request context or generated)
        - service (the emitting service name)
        - tool_name (which tool was called)
        - actor (user/API key identity from auth context)
        - parameters (redacted — no secrets/tokens/passwords)
        - outcome ("success" | "error")
        - duration_ms (wall clock time)
        - timestamp (ISO 8601)
        - error_detail (if outcome is "error")
    """
    effective_redact = redact_fields or _DEFAULT_REDACT_FIELDS
    log = logger or logging.getLogger(f"cloud_dog_api_kit.mcp.audit.{service}")

    def _wrapped(**kwargs: Any) -> Any:
        correlation_id = str(uuid.uuid4().hex[:16])
        ts = datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
        safe_params = _redact_params(kwargs, effective_redact)
        t0 = time.monotonic()
        try:
            result = handler(**kwargs)
            duration_ms = round((time.monotonic() - t0) * 1000, 2)
            log.info(
                "mcp_tool_call",
                extra={
                    "event_type": "mcp_tool_call",
                    "correlation_id": correlation_id,
                    "service": service,
                    "tool_name": tool_name,
                    "parameters": safe_params,
                    "outcome": "success",
                    "duration_ms": duration_ms,
                    "timestamp": ts,
                },
            )
            return result
        except Exception as exc:
            duration_ms = round((time.monotonic() - t0) * 1000, 2)
            log.warning(
                "mcp_tool_call",
                extra={
                    "event_type": "mcp_tool_call",
                    "correlation_id": correlation_id,
                    "service": service,
                    "tool_name": tool_name,
                    "parameters": safe_params,
                    "outcome": "error",
                    "duration_ms": duration_ms,
                    "timestamp": ts,
                    "error_detail": str(exc),
                },
            )
            raise

    _wrapped.__name__ = handler.__name__ if hasattr(handler, "__name__") else tool_name
    _wrapped.__doc__ = handler.__doc__
    return _wrapped
