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

"""UT1.4: Error Exceptions — exception instantiation and attributes."""

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


class TestErrorExceptions:
    def test_api_error_defaults(self) -> None:
        err = APIError()
        assert err.message == "An internal error occurred"
        assert err.status_code == 500
        assert err.details is None

    def test_custom_message(self) -> None:
        err = NotFoundError(message="User not found")
        assert str(err) == "User not found"
        assert err.message == "User not found"

    def test_custom_details(self) -> None:
        err = ValidationError(message="Bad input", details={"field": "name is required"})
        assert err.details == {"field": "name is required"}

    def test_retryable_override(self) -> None:
        err = InternalError(retryable=True)
        assert err.retryable is True

    def test_unauthenticated_defaults(self) -> None:
        err = UnauthenticatedError()
        assert err.status_code == 401
        assert err.code == "UNAUTHENTICATED"

    def test_unauthorised_defaults(self) -> None:
        err = UnauthorisedError()
        assert err.status_code == 403
        assert err.code == "UNAUTHORISED"

    def test_conflict_defaults(self) -> None:
        err = ConflictError()
        assert err.status_code == 409

    def test_rate_limit_retryable(self) -> None:
        err = RateLimitError()
        assert err.retryable is True
        assert err.status_code == 429

    def test_timeout_retryable(self) -> None:
        err = TimeoutError()
        assert err.retryable is True
        assert err.status_code == 504

    def test_upstream_retryable(self) -> None:
        err = UpstreamError()
        assert err.retryable is True
        assert err.status_code == 502

    def test_exceptions_are_exceptions(self) -> None:
        for cls in [
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
        ]:
            assert issubclass(cls, Exception)
