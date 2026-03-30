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

# cloud_dog_api_kit — Error response envelopes
#
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Standard error envelope models and helpers.
# Related requirements: FR1.2
# Related architecture: SA1, CC1.1

"""Error response envelope models for cloud_dog_api_kit."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from cloud_dog_api_kit.envelopes.success import Meta


class ErrorDetail(BaseModel):
    """Standard error detail within the error envelope.

    Attributes:
        code: Stable, machine-readable error code from the taxonomy.
        message: Human-readable summary (no secrets, no stack traces).
        details: Optional field-level error details.
        retryable: Whether the client can retry the request.

    Related tests: UT1.2_ErrorEnvelope, UT1.3_ErrorTaxonomy
    """

    code: str
    message: str
    details: dict[str, Any] | None = None
    retryable: bool = False


class ErrorResponse(BaseModel):
    """Standard error response envelope.

    Related tests: UT1.2_ErrorEnvelope
    """

    ok: bool = False
    error: ErrorDetail
    meta: Meta = Field(default_factory=Meta)


def error_envelope(
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
    retryable: bool = False,
    request_id: str = "",
    correlation_id: str | None = None,
) -> dict[str, Any]:
    """Build an error response envelope dictionary.

    Related tests: UT1.2_ErrorEnvelope
    """
    return {
        "ok": False,
        "error": {
            "code": code,
            "message": message,
            "details": details,
            "retryable": retryable,
        },
        "meta": {
            "request_id": request_id,
            "correlation_id": correlation_id,
        },
    }
