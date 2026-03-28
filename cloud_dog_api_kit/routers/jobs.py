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

# cloud_dog_api_kit — Job submission endpoint factory
#
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Helpers for creating job submission and status endpoints.
#   Long-running tasks MUST be represented as jobs with status polling.
# Related requirements: FR7.1, FR7.2
# Related architecture: CC1.12

"""Job submission endpoint factory for cloud_dog_api_kit."""

from __future__ import annotations

from typing import Any, Callable

from fastapi import APIRouter, Depends, Request

from cloud_dog_api_kit.envelopes.success import success_envelope
from cloud_dog_api_kit.correlation.context import get_request_id


def create_job_endpoint(
    resource: str,
    submit_fn: Callable,
    auth_dependency: Callable | None = None,
) -> APIRouter:
    """Create a job submission endpoint for a resource.

    Generates:
    - ``POST /{resource}:run`` — submit a job, returns ``{job_id: ...}``

    Args:
        resource: The resource name (e.g., ``queries``).
        submit_fn: Async callable that accepts a dict and returns a job_id string.
        auth_dependency: Optional auth dependency.

    Returns:
        A configured APIRouter with the job submission endpoint.

    Related tests: UT1.19_JobRouter, ST1.8_JobFlowEndToEnd
    """
    deps = [Depends(auth_dependency)] if auth_dependency else []
    router = APIRouter(tags=[resource])

    @router.post(f"/{resource}:run", dependencies=deps)
    async def submit_job(request: Request) -> dict[str, Any]:
        """Submit a long-running job."""
        body = await request.json()
        job_id = await submit_fn(body)
        return success_envelope(
            data={"job_id": job_id},
            request_id=get_request_id(),
        )

    return router
