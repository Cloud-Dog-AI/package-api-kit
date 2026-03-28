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

# cloud_dog_api_kit — CRUD router factory
#
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Standard CRUD route helper factory for resources. Generates
#   POST (create), GET (read/list), PATCH (update), DELETE (soft-delete) routes.
# Related requirements: FR4.1, FR4.2
# Related architecture: CC1.11

"""CRUD router factory for cloud_dog_api_kit."""

from typing import Any, Callable, Dict, Protocol, Type, runtime_checkable

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel

from cloud_dog_api_kit.envelopes.success import success_envelope
from cloud_dog_api_kit.errors.exceptions import NotFoundError
from cloud_dog_api_kit.schemas.pagination import PaginationParams, get_pagination, paginated_envelope
from cloud_dog_api_kit.correlation.context import get_request_id


@runtime_checkable
class CRUDService(Protocol):
    """Protocol for CRUD service implementations.

    Services MUST implement these methods to work with create_crud_router.

    Related tests: UT1.16_CRUDRouter
    """

    async def create(self, data: dict[str, Any]) -> dict[str, Any]:
        """Create a resource from the provided payload."""
        ...

    async def get(self, resource_id: str) -> dict[str, Any] | None:
        """Return a single resource by identifier."""
        ...

    async def list(
        self, pagination: PaginationParams, filters: dict[str, Any] | None = None
    ) -> tuple[list[dict[str, Any]], int]:
        """List resources for the requested page and filters."""
        ...

    async def update(self, resource_id: str, data: dict[str, Any]) -> dict[str, Any] | None:
        """Update a resource with the supplied partial payload."""
        ...

    async def delete(self, resource_id: str) -> bool:
        """Delete a resource by identifier."""
        ...


def create_versioned_router(prefix: str = "/api/v1") -> APIRouter:
    """Create a versioned API router with the standard prefix.

    Args:
        prefix: The URL prefix. Defaults to ``/api/v1``.

    Returns:
        A configured APIRouter.

    Related tests: ST1.6_AppFactory
    """
    return APIRouter(prefix=prefix)


def create_crud_router(
    resource_name: str,
    model: Type[BaseModel],
    service: Any,
    auth_dependency: Callable | None = None,
) -> APIRouter:
    """Create a standard CRUD router for a resource.

    Generates routes:
    - ``POST /{resource}`` — create
    - ``GET /{resource}/{id}`` — read
    - ``GET /{resource}`` — list (paged)
    - ``PATCH /{resource}/{id}`` — partial update
    - ``DELETE /{resource}/{id}`` — soft-delete

    All routes use the standard success/error envelopes.

    Args:
        resource_name: The pluralised resource name (e.g., ``users``).
        model: The Pydantic model for the resource.
        service: A service implementing the CRUDService protocol.
        auth_dependency: Optional auth dependency for protected routes.

    Returns:
        A configured APIRouter with CRUD endpoints.

    Related tests: UT1.16_CRUDRouter, ST1.7_CRUDFlowEndToEnd
    """
    deps = [Depends(auth_dependency)] if auth_dependency else []
    router = APIRouter(prefix=f"/{resource_name}", tags=[resource_name])

    @router.post("", dependencies=deps)
    async def create_resource(request: Request) -> Dict[str, Any]:
        """Create a new resource."""
        raw = await request.json()
        validated = model(**raw)
        result = await service.create(validated.model_dump())
        return success_envelope(data=result, request_id=get_request_id())

    @router.get("/{resource_id}", dependencies=deps)
    async def get_resource(resource_id: str) -> dict[str, Any]:
        """Get a resource by ID."""
        result = await service.get(resource_id)
        if result is None:
            raise NotFoundError(message=f"{resource_name} '{resource_id}' not found")
        return success_envelope(data=result, request_id=get_request_id())

    @router.get("", dependencies=deps)
    async def list_resources(
        request: Request,
        offset: int = Query(default=0, ge=0, description="Starting offset"),
        limit: int = Query(default=50, ge=1, le=1000, description="Page size"),
        sort: str | None = Query(default=None, description="Sort field (e.g., created_at:desc)"),
    ) -> dict[str, Any]:
        """List resources with pagination."""
        # Use direct query parameters instead of Depends(get_pagination) because
        # BaseHTTPMiddleware + dependency injection can deadlock under ASGITransport.
        pagination = get_pagination(offset=offset, limit=limit, sort=sort)
        filters = dict(request.query_params)
        for key in ("offset", "limit", "sort"):
            filters.pop(key, None)

        items, total = await service.list(pagination, filters if filters else None)
        return paginated_envelope(
            items=items,
            limit=pagination.limit,
            offset=pagination.offset,
            total=total,
            has_more=(pagination.offset + pagination.limit) < total,
            request_id=get_request_id(),
        )

    @router.patch("/{resource_id}", dependencies=deps)
    async def update_resource(resource_id: str, request: Request) -> Dict[str, Any]:
        """Partial update a resource."""
        raw = await request.json()
        validated = model(**raw)
        result = await service.update(resource_id, validated.model_dump(exclude_unset=True))
        if result is None:
            raise NotFoundError(message=f"{resource_name} '{resource_id}' not found")
        return success_envelope(data=result, request_id=get_request_id())

    @router.delete("/{resource_id}", dependencies=deps)
    async def delete_resource(resource_id: str) -> dict[str, Any]:
        """Soft-delete a resource."""
        deleted = await service.delete(resource_id)
        if not deleted:
            raise NotFoundError(message=f"{resource_name} '{resource_id}' not found")
        return success_envelope(data={"deleted": True}, request_id=get_request_id())

    return router
