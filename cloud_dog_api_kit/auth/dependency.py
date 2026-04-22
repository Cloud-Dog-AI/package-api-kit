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

# cloud_dog_api_kit — Authentication dependency for FastAPI
#
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: FastAPI dependency factory for API key / Bearer authentication.
#   Supports both API key and Bearer token with configurable verify functions.
# Related requirements: FR3.4, FR3.5
# Related architecture: CC1.5

"""Authentication dependency factory for FastAPI."""

from __future__ import annotations

from typing import Any, Callable

from fastapi import Request

from cloud_dog_api_kit.errors.exceptions import UnauthenticatedError


def create_auth_dependency(
    api_key_header: str = "X-API-Key",
    bearer_verify_fn: Callable | None = None,
    api_key_verify_fn: Callable | None = None,
    config_api_key: str | None = None,
) -> Callable:
    """Create a FastAPI dependency for API key / Bearer authentication.

    The dependency tries Bearer token first, then falls back to API key.
    On success, sets ``request.state.user``, ``request.state.api_key``,
    and ``request.state.tenant_id``.

    Args:
        api_key_header: Header name for API key. Defaults to ``X-API-Key``.
        bearer_verify_fn: Async/sync callable to verify Bearer tokens.
            Should return a dict with ``user_id``, ``roles``, ``tenant_id``.
        api_key_verify_fn: Async/sync callable to verify API keys.
            Should return a dict with ``user_id``, ``roles``, ``tenant_id``.
        config_api_key: Static API key from config for simple verification.

    Returns:
        A FastAPI dependency callable.

    Related tests: UT1.6_AuthDependency, UT1.7_BearerAuth, UT1.10_ServiceAuth
    """

    async def _auth_dependency(request: Request) -> dict[str, Any]:
        # Try Bearer token first
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()
            if not token:
                raise UnauthenticatedError(message="Empty Bearer token")
            if bearer_verify_fn is not None:
                import asyncio

                if asyncio.iscoroutinefunction(bearer_verify_fn):
                    result = await bearer_verify_fn(token)
                else:
                    result = bearer_verify_fn(token)
                if result is None:
                    raise UnauthenticatedError(message="Invalid Bearer token")
                _set_request_state(request, result)
                return result
            raise UnauthenticatedError(message="Bearer token verification not configured")

        # Try API key
        api_key = request.headers.get(api_key_header.lower(), "") or request.headers.get(api_key_header, "")
        if not api_key:
            raise UnauthenticatedError(message="Missing credentials")

        if api_key_verify_fn is not None:
            import asyncio

            if asyncio.iscoroutinefunction(api_key_verify_fn):
                result = await api_key_verify_fn(api_key)
            else:
                result = api_key_verify_fn(api_key)
            if result is None:
                raise UnauthenticatedError(message="Invalid API key")
            _set_request_state(request, result)
            return result

        # Fall back to config-based verification
        if config_api_key is not None:
            if api_key == config_api_key:
                result = {"user_id": "api_key_user", "roles": [], "tenant_id": None}
                _set_request_state(request, result)
                return result
            raise UnauthenticatedError(message="Invalid API key")

        raise UnauthenticatedError(message="No authentication method configured")

    return _auth_dependency


def _set_request_state(request: Request, auth_result: dict[str, Any]) -> None:
    """Set authentication result on request state.

    Args:
        request: The FastAPI request.
        auth_result: Dict with user_id, roles, tenant_id.
    """
    request.state.user = auth_result.get("user_id")
    request.state.api_key = True
    request.state.tenant_id = auth_result.get("tenant_id")
    request.state.roles = auth_result.get("roles", [])
