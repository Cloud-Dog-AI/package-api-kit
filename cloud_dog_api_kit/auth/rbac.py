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

# cloud_dog_api_kit — RBAC helpers
#
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Role-based access control helpers for endpoint-level authorisation.
#   Default-deny: all endpoints require auth unless explicitly marked public.
# Related requirements: FR3.3
# Related architecture: CC1.6

"""RBAC helpers for cloud_dog_api_kit."""

from __future__ import annotations

from typing import Callable

from fastapi import Request

from cloud_dog_api_kit.errors.exceptions import UnauthorisedError


def require_permission(permission: str) -> Callable:
    """Create a FastAPI dependency that checks for a specific permission.

    Args:
        permission: The required permission string.

    Returns:
        A FastAPI dependency callable that raises UnauthorisedError if
        the user does not have the required permission.

    Related tests: UT1.8_RBACHelpers, SEC1.2_RBACEnforcement
    """

    async def _check(request: Request) -> None:
        roles = getattr(request.state, "roles", []) or []
        permissions = getattr(request.state, "permissions", []) or []
        all_perms = set(roles) | set(permissions)
        if permission not in all_perms:
            raise UnauthorisedError(message=f"Missing required permission: {permission}")

    return _check


def require_admin() -> Callable:
    """Create a FastAPI dependency that checks for admin role.

    Returns:
        A FastAPI dependency callable that raises UnauthorisedError if
        the user does not have the admin role.

    Related tests: UT1.8_RBACHelpers, SEC1.2_RBACEnforcement
    """

    async def _check(request: Request) -> None:
        roles = getattr(request.state, "roles", []) or []
        if "admin" not in roles:
            raise UnauthorisedError(message="Admin access required")

    return _check


def require_tenant(tenant_id_param: str = "tenant_id") -> Callable:
    """Create a FastAPI dependency that enforces tenant isolation.

    Checks that the authenticated user's tenant_id matches the requested
    tenant_id from the path or query parameters.

    Args:
        tenant_id_param: The name of the path/query parameter containing
            the tenant ID. Defaults to ``tenant_id``.

    Returns:
        A FastAPI dependency callable that raises UnauthorisedError on
        tenant mismatch.

    Related tests: UT1.9_TenantIsolation, SEC1.3_TenantIsolation
    """

    async def _check(request: Request) -> None:
        user_tenant = getattr(request.state, "tenant_id", None)
        if user_tenant is None:
            return  # No tenant context — skip check

        # Check path params
        requested_tenant = request.path_params.get(tenant_id_param)
        if requested_tenant is None:
            # Check query params
            requested_tenant = request.query_params.get(tenant_id_param)

        if requested_tenant is not None and requested_tenant != user_tenant:
            raise UnauthorisedError(message="Access denied: tenant mismatch")

    return _check
