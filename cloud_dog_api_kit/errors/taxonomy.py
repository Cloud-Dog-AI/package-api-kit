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

# cloud_dog_api_kit — Error taxonomy
#
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Stable error code taxonomy (9 codes) per PS-20.
# Related requirements: FR1.3
# Related architecture: SA1, CC1.3

"""Error code taxonomy for cloud_dog_api_kit."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ErrorTaxonomyEntry:
    """One error taxonomy entry."""

    code: str
    http_status: int
    retryable: bool


UNAUTHENTICATED = ErrorTaxonomyEntry(code="UNAUTHENTICATED", http_status=401, retryable=False)
UNAUTHORISED = ErrorTaxonomyEntry(code="UNAUTHORISED", http_status=403, retryable=False)
NOT_FOUND = ErrorTaxonomyEntry(code="NOT_FOUND", http_status=404, retryable=False)
CONFLICT = ErrorTaxonomyEntry(code="CONFLICT", http_status=409, retryable=False)
INVALID_REQUEST = ErrorTaxonomyEntry(code="INVALID_REQUEST", http_status=422, retryable=False)
RATE_LIMITED = ErrorTaxonomyEntry(code="RATE_LIMITED", http_status=429, retryable=True)
TIMEOUT = ErrorTaxonomyEntry(code="TIMEOUT", http_status=504, retryable=True)
UPSTREAM_ERROR = ErrorTaxonomyEntry(code="UPSTREAM_ERROR", http_status=502, retryable=True)
INTERNAL_ERROR = ErrorTaxonomyEntry(code="INTERNAL_ERROR", http_status=500, retryable=False)


ALL_ENTRIES: tuple[ErrorTaxonomyEntry, ...] = (
    UNAUTHENTICATED,
    UNAUTHORISED,
    NOT_FOUND,
    CONFLICT,
    INVALID_REQUEST,
    RATE_LIMITED,
    TIMEOUT,
    UPSTREAM_ERROR,
    INTERNAL_ERROR,
)

BY_CODE: dict[str, ErrorTaxonomyEntry] = {e.code: e for e in ALL_ENTRIES}
