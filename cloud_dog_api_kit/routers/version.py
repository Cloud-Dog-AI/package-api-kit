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

# cloud_dog_api_kit — Version endpoint router
#
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Provides a standard `/api/v1/version` endpoint for services.
# Related requirements: FR10.3
# Related architecture: SA1

"""Version endpoint router."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter


def create_version_router(
    api_prefix: str,
    application_name: str,
    version: str,
    api_version: str = "v1",
) -> APIRouter:
    """Create a router exposing `/version` under the given API prefix."""
    router = APIRouter(prefix=api_prefix, tags=["system"])

    @router.get("/version")
    async def api_version_endpoint() -> dict[str, Any]:
        """Handle api version endpoint."""
        return {"application": application_name, "version": version, "api_version": api_version}

    return router
