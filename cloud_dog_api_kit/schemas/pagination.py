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

# cloud_dog_api_kit — Pagination models and dependency
#
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: PaginationParams dataclass and FastAPI dependency for extracting
#   pagination, sort, and filter parameters from list requests.
# Related requirements: FR4.3
# Related architecture: CC1.10

"""Pagination models and FastAPI dependency."""

from __future__ import annotations

from typing import Any, Generic, TypeVar
from dataclasses import dataclass

from fastapi import Query
from pydantic import BaseModel


@dataclass
class PaginationParams:
    """Pagination, sorting, and filtering parameters.

    Attributes:
        offset: The starting offset. Defaults to 0.
        limit: The page size. Defaults to 50.
        sort: The field to sort by, or None for default ordering.
        sort_dir: Sort direction — ``asc`` or ``desc``. Defaults to ``asc``.

    Related tests: UT1.13_PaginationModels, UT1.14_PaginationDependency
    """

    offset: int = 0
    limit: int = 50
    sort: str | None = None
    sort_dir: str = "asc"


def get_pagination(
    offset: int = Query(default=0, ge=0, description="Starting offset"),
    limit: int = Query(default=50, ge=1, le=1000, description="Page size"),
    sort: str | None = Query(default=None, description="Sort field (e.g., created_at:desc)"),
) -> PaginationParams:
    """FastAPI dependency for extracting pagination + sort parameters.

    Parses the ``sort`` parameter if it contains a colon-separated direction
    (e.g., ``created_at:desc``).

    Args:
        offset: Starting offset (query param).
        limit: Page size (query param).
        sort: Sort specification (query param).

    Returns:
        A populated PaginationParams instance.

    Related tests: UT1.14_PaginationDependency
    """
    sort_field = sort
    sort_dir = "asc"
    if sort and ":" in sort:
        parts = sort.rsplit(":", 1)
        sort_field = parts[0]
        if parts[1].lower() in ("asc", "desc"):
            sort_dir = parts[1].lower()

    return PaginationParams(
        offset=offset,
        limit=limit,
        sort=sort_field,
        sort_dir=sort_dir,
    )


class PageInfo(BaseModel):
    """Pagination metadata for list responses.

    Related tests: UT1.13_PaginationModels
    """

    limit: int
    offset: int
    total: int | None = None
    has_more: bool
    cursor: str | None = None


T = TypeVar("T")


class PaginatedData(BaseModel, Generic[T]):
    """Paginated list data within the success envelope.

    Related tests: UT1.13_PaginationModels
    """

    items: list[T]
    page: PageInfo


def paginated_envelope(
    items: list[Any],
    limit: int,
    offset: int,
    total: int | None = None,
    has_more: bool = False,
    cursor: str | None = None,
    request_id: str = "",
    correlation_id: str | None = None,
    version: str = "v1",
) -> dict[str, Any]:
    """Build a paginated success response envelope dictionary.

    Related tests: UT1.13_PaginationModels
    """
    return {
        "ok": True,
        "data": {
            "items": items,
            "page": {
                "limit": limit,
                "offset": offset,
                "total": total,
                "has_more": has_more,
                "cursor": cursor,
            },
        },
        "meta": {
            "request_id": request_id,
            "correlation_id": correlation_id,
            "version": version,
        },
    }
