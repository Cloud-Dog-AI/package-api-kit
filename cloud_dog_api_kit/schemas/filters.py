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

# cloud_dog_api_kit — Filter and sort helpers
#
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Helpers for parsing sort and filter parameters from list requests.
# Related requirements: FR4.3
# Related architecture: CC1.10

"""Filter and sort helpers for cloud_dog_api_kit."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class SortParams(BaseModel):
    """Base model for sort parameters.

    Related tests: UT1.15_FilterHelpers
    """

    sort: str | None = Field(default=None, description="Sort field (e.g., created_at)")
    sort_dir: str = Field(default="asc", description="Sort direction: asc|desc")


class FilterParams(BaseModel):
    """Base model for filter parameters.

    This is intentionally permissive: concrete services should subclass it.

    Related tests: UT1.15_FilterHelpers
    """

    model_config = {"extra": "allow"}


def parse_sort(sort_str: str | None) -> tuple[str | None, str]:
    """Parse a sort specification string into field and direction.

    Format: ``field_name`` or ``field_name:asc`` or ``field_name:desc``.

    Args:
        sort_str: The sort specification string, or None.

    Returns:
        A tuple of (field_name, direction). Direction defaults to ``asc``.

    Related tests: UT1.15_FilterHelpers
    """
    if not sort_str:
        return None, "asc"

    if ":" in sort_str:
        parts = sort_str.rsplit(":", 1)
        direction = parts[1].lower() if parts[1].lower() in ("asc", "desc") else "asc"
        return parts[0], direction

    return sort_str, "asc"


def parse_filters(query_params: dict[str, Any], allowed_fields: list[str] | None = None) -> dict[str, Any]:
    """Parse filter parameters from query params.

    Extracts query parameters that match allowed field names and returns
    them as a filter dictionary. Ignores pagination params (offset, limit, sort).

    Args:
        query_params: The raw query parameters dict.
        allowed_fields: Optional whitelist of filterable field names.
            If None, all non-pagination params are included.

    Returns:
        A dictionary of field→value filters.

    Related tests: UT1.15_FilterHelpers
    """
    pagination_keys = {"offset", "limit", "sort"}
    result: dict[str, Any] = {}

    for key, value in query_params.items():
        if key in pagination_keys:
            continue
        if allowed_fields is not None and key not in allowed_fields:
            continue
        result[key] = value

    return result
