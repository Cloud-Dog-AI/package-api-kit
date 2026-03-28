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

"""UT1.3: Error Taxonomy — error code catalogue tests."""

from __future__ import annotations
from cloud_dog_api_kit.errors.exceptions import (
    APIError,
    UnauthenticatedError,
    UnauthorisedError,
    NotFoundError,
    ConflictError,
    ValidationError,
    RateLimitError,
    TimeoutError,
    UpstreamError,
    InternalError,
)

EXPECTED_TAXONOMY = {
    "UNAUTHENTICATED": (401, False),
    "UNAUTHORISED": (403, False),
    "NOT_FOUND": (404, False),
    "CONFLICT": (409, False),
    "INVALID_REQUEST": (422, False),
    "RATE_LIMITED": (429, True),
    "TIMEOUT": (504, True),
    "UPSTREAM_ERROR": (502, True),
    "INTERNAL_ERROR": (500, False),
}


class TestErrorTaxonomy:
    def test_all_error_codes_exist(self) -> None:
        classes = [
            UnauthenticatedError,
            UnauthorisedError,
            NotFoundError,
            ConflictError,
            ValidationError,
            RateLimitError,
            TimeoutError,
            UpstreamError,
            InternalError,
        ]
        codes = {cls.code for cls in classes}
        assert codes == set(EXPECTED_TAXONOMY.keys())

    def test_status_codes_match(self) -> None:
        for cls in [
            UnauthenticatedError,
            UnauthorisedError,
            NotFoundError,
            ConflictError,
            ValidationError,
            RateLimitError,
            TimeoutError,
            UpstreamError,
            InternalError,
        ]:
            expected_status, _ = EXPECTED_TAXONOMY[cls.code]
            assert cls.status_code == expected_status, f"{cls.__name__} status mismatch"

    def test_retryable_flags_match(self) -> None:
        for cls in [
            UnauthenticatedError,
            UnauthorisedError,
            NotFoundError,
            ConflictError,
            ValidationError,
            RateLimitError,
            TimeoutError,
            UpstreamError,
            InternalError,
        ]:
            _, expected_retry = EXPECTED_TAXONOMY[cls.code]
            assert cls.retryable == expected_retry, f"{cls.__name__} retryable mismatch"

    def test_all_inherit_from_api_error(self) -> None:
        for cls in [
            UnauthenticatedError,
            UnauthorisedError,
            NotFoundError,
            ConflictError,
            ValidationError,
            RateLimitError,
            TimeoutError,
            UpstreamError,
            InternalError,
        ]:
            assert issubclass(cls, APIError)
