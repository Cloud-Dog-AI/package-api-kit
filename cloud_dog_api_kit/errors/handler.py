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

# cloud_dog_api_kit — Error handler registration for FastAPI
#
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Registers exception handlers that convert APIError subclasses,
#   RequestValidationError, and unhandled exceptions into standard error envelopes.
# Related requirements: FR2.2, CS1.1, CS1.5
# Related architecture: CC1.3

"""Error handler registration for FastAPI applications."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from starlette.responses import JSONResponse

from cloud_dog_api_kit.errors.exceptions import APIError
from cloud_dog_api_kit.envelopes.error import error_envelope

logger = logging.getLogger("cloud_dog_api_kit.errors")


def register_error_handlers(app: FastAPI) -> None:
    """Register standard error handlers on a FastAPI application.

    Converts:
    - APIError subclasses into the standard error envelope with correct HTTP status.
    - RequestValidationError into an INVALID_REQUEST envelope with field-level details.
    - Unhandled Exception into a generic 500 with no leaked internals.

    Args:
        app: The FastAPI application instance.

    Related tests: UT1.5_ErrorHandler, ST1.2_ErrorFlowEndToEnd, SEC1.6_ErrorSanitisation
    """

    @app.exception_handler(APIError)
    async def _api_error_handler(request: Request, exc: APIError) -> JSONResponse:
        request_id = getattr(request.state, "request_id", "")
        correlation_id = getattr(request.state, "correlation_id", None)
        body = error_envelope(
            code=exc.code,
            message=exc.message,
            details=exc.details,
            retryable=exc.retryable,
            request_id=request_id,
            correlation_id=correlation_id,
        )
        return JSONResponse(status_code=exc.status_code, content=body)

    @app.exception_handler(RequestValidationError)
    async def _validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        request_id = getattr(request.state, "request_id", "")
        correlation_id = getattr(request.state, "correlation_id", None)
        field_errors: dict[str, Any] = {}
        for error in exc.errors():
            loc = ".".join(str(part) for part in error.get("loc", []))
            field_errors[loc] = error.get("msg", "Validation error")
        body = error_envelope(
            code="INVALID_REQUEST",
            message="Validation failure",
            details=field_errors,
            retryable=False,
            request_id=request_id,
            correlation_id=correlation_id,
        )
        return JSONResponse(status_code=422, content=body)

    @app.exception_handler(Exception)
    async def _generic_error_handler(request: Request, exc: Exception) -> JSONResponse:
        request_id = getattr(request.state, "request_id", "")
        correlation_id = getattr(request.state, "correlation_id", None)
        logger.exception(
            "Unhandled exception",
            extra={"request_id": request_id, "path": request.url.path},
        )
        body = error_envelope(
            code="INTERNAL_ERROR",
            message="An internal error occurred",
            retryable=False,
            request_id=request_id,
            correlation_id=correlation_id,
        )
        return JSONResponse(status_code=500, content=body)
