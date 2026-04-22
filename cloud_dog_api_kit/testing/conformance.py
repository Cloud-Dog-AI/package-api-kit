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

# cloud_dog_api_kit — Conformance test helpers
#
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Conformance validators for verifying API responses match
#   the standard envelope schemas, pagination format, and correlation ID rules.
# Related requirements: FR16.2
# Related architecture: CC1.19

"""Conformance test helpers for cloud_dog_api_kit."""

from __future__ import annotations

from typing import Any


def validate_success_envelope(response_json: dict[str, Any]) -> list[str]:
    """Validate a response against the success envelope schema.

    Args:
        response_json: The parsed JSON response body.

    Returns:
        A list of validation error messages. Empty if valid.

    Related tests: UT1.35_ConformanceValidators
    """
    errors: list[str] = []
    if not isinstance(response_json, dict):
        return ["Response is not a dict"]

    if response_json.get("ok") is not True:
        errors.append("Missing or false 'ok' field")

    if "data" not in response_json:
        errors.append("Missing 'data' field")

    if "meta" not in response_json:
        errors.append("Missing 'meta' field")
    else:
        meta = response_json["meta"]
        if not isinstance(meta, dict):
            errors.append("'meta' is not a dict")
        else:
            if "request_id" not in meta:
                errors.append("Missing 'meta.request_id'")

    return errors


def validate_error_envelope(response_json: dict[str, Any]) -> list[str]:
    """Validate a response against the error envelope schema.

    Args:
        response_json: The parsed JSON response body.

    Returns:
        A list of validation error messages. Empty if valid.

    Related tests: UT1.35_ConformanceValidators
    """
    errors: list[str] = []
    if not isinstance(response_json, dict):
        return ["Response is not a dict"]

    if response_json.get("ok") is not False:
        errors.append("'ok' field should be false")

    if "error" not in response_json:
        errors.append("Missing 'error' field")
    else:
        error = response_json["error"]
        if not isinstance(error, dict):
            errors.append("'error' is not a dict")
        else:
            if "code" not in error:
                errors.append("Missing 'error.code'")
            if "message" not in error:
                errors.append("Missing 'error.message'")
            if "retryable" not in error:
                errors.append("Missing 'error.retryable'")

    if "meta" not in response_json:
        errors.append("Missing 'meta' field")

    return errors


def validate_pagination_response(response_json: dict[str, Any]) -> list[str]:
    """Validate a paginated list response.

    Args:
        response_json: The parsed JSON response body.

    Returns:
        A list of validation error messages. Empty if valid.

    Related tests: UT1.35_ConformanceValidators
    """
    errors = validate_success_envelope(response_json)
    if errors:
        return errors

    data = response_json.get("data", {})
    if "items" not in data:
        errors.append("Missing 'data.items'")
    elif not isinstance(data["items"], list):
        errors.append("'data.items' is not a list")

    if "page" not in data:
        errors.append("Missing 'data.page'")
    else:
        page = data["page"]
        if not isinstance(page, dict):
            errors.append("'data.page' is not a dict")
        else:
            for field in ("limit", "offset", "has_more"):
                if field not in page:
                    errors.append(f"Missing 'data.page.{field}'")

    return errors


def validate_correlation_id(response_headers: dict[str, str]) -> list[str]:
    """Validate that correlation ID is present in response headers.

    Args:
        response_headers: The HTTP response headers.

    Returns:
        A list of validation error messages. Empty if valid.

    Related tests: UT1.35_ConformanceValidators
    """
    errors: list[str] = []
    # Check for X-Request-Id (case-insensitive)
    header_keys_lower = {k.lower(): v for k, v in response_headers.items()}
    if "x-request-id" not in header_keys_lower:
        errors.append("Missing X-Request-Id response header")
    elif not header_keys_lower["x-request-id"]:
        errors.append("Empty X-Request-Id response header")
    return errors
