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

# cloud_dog_api_kit — Legacy MCP error mapper
#
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Compatibility mapper for legacy MCP payloads that do not use
#   standard PS-20 success/error envelopes.
# Related requirements: FR18.1
# Related architecture: SA1

"""Legacy MCP payload mapping utilities."""

from __future__ import annotations

from typing import Any

from cloud_dog_api_kit.envelopes import error_envelope, success_envelope


def map_legacy_mcp_payload(
    payload: Any,
    *,
    request_id: str = "",
    correlation_id: str | None = None,
) -> dict[str, Any]:
    """Map legacy MCP payload shapes to standard envelopes."""
    if isinstance(payload, dict) and "ok" in payload and ("data" in payload or "error" in payload):
        mapped = dict(payload)
        meta = dict(mapped.get("meta") or {})
        meta.setdefault("request_id", request_id)
        if correlation_id is not None:
            meta.setdefault("correlation_id", correlation_id)
        mapped["meta"] = meta
        return mapped

    if isinstance(payload, dict):
        if payload.get("success") is False:
            return error_envelope(
                code=str(payload.get("code", "INTERNAL_ERROR")),
                message=str(payload.get("message", "Request failed")),
                details=payload.get("details"),
                retryable=bool(payload.get("retryable", False)),
                request_id=request_id,
                correlation_id=correlation_id,
            )
        if "error" in payload:
            error_value = payload.get("error")
            if isinstance(error_value, dict):
                code = str(error_value.get("code", payload.get("code", "INTERNAL_ERROR")))
                message = str(error_value.get("message", payload.get("message", "Request failed")))
                details = error_value.get("details", payload.get("details"))
                retryable = bool(error_value.get("retryable", payload.get("retryable", False)))
            else:
                code = str(payload.get("code", "INTERNAL_ERROR"))
                message = str(error_value)
                details = payload.get("details")
                retryable = bool(payload.get("retryable", False))
            return error_envelope(
                code=code,
                message=message,
                details=details,
                retryable=retryable,
                request_id=request_id,
                correlation_id=correlation_id,
            )

    return success_envelope(
        data=payload,
        request_id=request_id,
        correlation_id=correlation_id,
    )
