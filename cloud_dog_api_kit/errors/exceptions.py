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

# cloud_dog_api_kit — Typed exception classes
#
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Exception hierarchy mapping to the PS-20 error taxonomy.
#   Each exception carries code, message, retryable, and optional details.
# Related requirements: FR2.1
# Related architecture: CC1.3

"""Typed exception classes for the PS-20 error taxonomy."""

from __future__ import annotations

from typing import Any


class APIError(Exception):
    """Base exception for all API errors.

    Attributes:
        status_code: HTTP status code.
        code: Machine-readable error code from the taxonomy.
        message: Human-readable error message.
        retryable: Whether the client can retry.
        details: Optional field-level error details.

    Related tests: UT1.4_ErrorExceptions
    """

    status_code: int = 500
    code: str = "INTERNAL_ERROR"
    retryable: bool = False

    def __init__(
        self,
        message: str = "An internal error occurred",
        details: dict[str, Any] | None = None,
        retryable: bool | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.details = details
        if retryable is not None:
            self.retryable = retryable


class UnauthenticatedError(APIError):
    """Missing or invalid credentials (401).

    Related tests: UT1.4_ErrorExceptions
    """

    status_code = 401
    code = "UNAUTHENTICATED"
    retryable = False

    def __init__(self, message: str = "Missing or invalid credentials", **kwargs: Any) -> None:
        super().__init__(message=message, **kwargs)


class UnauthorisedError(APIError):
    """Insufficient permissions (403).

    Related tests: UT1.4_ErrorExceptions
    """

    status_code = 403
    code = "UNAUTHORISED"
    retryable = False

    def __init__(self, message: str = "Insufficient permissions", **kwargs: Any) -> None:
        super().__init__(message=message, **kwargs)


class NotFoundError(APIError):
    """Resource does not exist (404).

    Related tests: UT1.4_ErrorExceptions
    """

    status_code = 404
    code = "NOT_FOUND"
    retryable = False

    def __init__(self, message: str = "Resource not found", **kwargs: Any) -> None:
        super().__init__(message=message, **kwargs)


class ConflictError(APIError):
    """Resource state conflict (409).

    Related tests: UT1.4_ErrorExceptions
    """

    status_code = 409
    code = "CONFLICT"
    retryable = False

    def __init__(self, message: str = "Resource state conflict", **kwargs: Any) -> None:
        super().__init__(message=message, **kwargs)


class ValidationError(APIError):
    """Validation failure (422).

    Related tests: UT1.4_ErrorExceptions
    """

    status_code = 422
    code = "INVALID_REQUEST"
    retryable = False

    def __init__(self, message: str = "Validation failure", **kwargs: Any) -> None:
        super().__init__(message=message, **kwargs)


class RateLimitError(APIError):
    """Too many requests (429).

    Related tests: UT1.4_ErrorExceptions
    """

    status_code = 429
    code = "RATE_LIMITED"
    retryable = True

    def __init__(self, message: str = "Too many requests", **kwargs: Any) -> None:
        super().__init__(message=message, **kwargs)


class TimeoutError(APIError):
    """Operation timed out (504).

    Related tests: UT1.4_ErrorExceptions
    """

    status_code = 504
    code = "TIMEOUT"
    retryable = True

    def __init__(self, message: str = "Operation timed out", **kwargs: Any) -> None:
        super().__init__(message=message, **kwargs)


class UpstreamError(APIError):
    """Downstream service failure (502).

    Related tests: UT1.4_ErrorExceptions
    """

    status_code = 502
    code = "UPSTREAM_ERROR"
    retryable = True

    def __init__(self, message: str = "Downstream service failure", **kwargs: Any) -> None:
        super().__init__(message=message, **kwargs)


class InternalError(APIError):
    """Unhandled server error (500).

    Related tests: UT1.4_ErrorExceptions
    """

    status_code = 500
    code = "INTERNAL_ERROR"
    retryable = False

    def __init__(self, message: str = "An internal error occurred", **kwargs: Any) -> None:
        super().__init__(message=message, **kwargs)
