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

# cloud_dog_api_kit — Success response envelopes
#
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Standard success envelope models and helpers.
# Related requirements: FR1.1
# Related architecture: SA1, CC1.1

"""Success response envelope models for cloud_dog_api_kit."""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class Meta(BaseModel):
    """Response metadata included in every envelope.

    Attributes:
        request_id: The unique request identifier (correlation ID).
        correlation_id: Optional cross-service correlation identifier.
        version: API version string.

    Related tests: UT1.1_SuccessEnvelope
    """

    request_id: str = ""
    correlation_id: str | None = None
    version: str = "v1"


class SuccessResponse(BaseModel, Generic[T]):
    """Standard success response envelope.

    Attributes:
        ok: Always True for success responses.
        data: The response payload.
        meta: Response metadata.

    Related tests: UT1.1_SuccessEnvelope
    """

    ok: bool = True
    data: T
    meta: Meta = Field(default_factory=Meta)


def success_envelope(
    data: Any,
    request_id: str = "",
    correlation_id: str | None = None,
    version: str = "v1",
) -> dict[str, Any]:
    """Build a success response envelope dictionary.

    Related tests: UT1.1_SuccessEnvelope
    """
    return {
        "ok": True,
        "data": data,
        "meta": {
            "request_id": request_id,
            "correlation_id": correlation_id,
            "version": version,
        },
    }
