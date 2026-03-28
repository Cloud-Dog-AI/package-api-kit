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

# cloud_dog_api_kit — Health router factory
#
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Configurable health/readiness/liveness router with optional
#   dependency checks and authenticated /status endpoint.
# Related requirements: FR6.1
# Related architecture: CC1.9

"""Health router factory for cloud_dog_api_kit."""

from __future__ import annotations

from typing import Any, Callable, Protocol

from fastapi import APIRouter, Depends


class HealthCheck(Protocol):
    """Protocol for health check callables.

    Each health check returns a dict with at minimum ``status`` (``ok`` or ``error``)
    and optionally additional diagnostic fields.
    """

    async def __call__(self) -> dict[str, Any]: ...


def create_health_router(
    application_name: str,
    version: str = "0.0.0",
    env_file: str | None = None,
    checks: dict[str, Callable] | None = None,
    auth_dependency: Callable | None = None,
) -> APIRouter:
    """Create a health/readiness/liveness router.

    Endpoints:
    - ``GET /health`` — Liveness (no auth).
    - ``GET /ready`` — Readiness (no auth).
    - ``GET /live`` — Liveness alias (no auth).
    - ``GET /status`` — Full status with dependency checks (requires auth).

    Args:
        application_name: The application/service name.
        version: The application version string.
        env_file: The env file path (for diagnostics).
        checks: Optional named health check callables.
        auth_dependency: FastAPI dependency for /status authentication.

    Returns:
        A configured APIRouter with health endpoints.

    Related tests: UT1.17_HealthRouter, UT1.18_ReadyLiveEndpoints, ST1.5_HealthStatusEndToEnd
    """
    router = APIRouter(tags=["health"])

    @router.get("/health")
    async def health() -> dict[str, Any]:
        """Liveness probe — returns application name, version, env_file."""
        return {
            "status": "ok",
            "application": application_name,
            "version": version,
            "env_file": env_file,
        }

    @router.get("/ready")
    async def ready() -> dict[str, Any]:
        """Readiness probe — returns OK only when all critical dependencies are up."""
        if not checks:
            return {"status": "ok", "checks": {}}

        results: dict[str, Any] = {}
        all_ok = True
        for name, check_fn in checks.items():
            try:
                result = await check_fn()
                results[name] = result
                if result.get("status") != "ok":
                    all_ok = False
            except Exception as exc:
                results[name] = {"status": "error", "message": str(exc)}
                all_ok = False

        return {
            "status": "ok" if all_ok else "degraded",
            "checks": results,
        }

    @router.get("/live")
    async def live() -> dict[str, Any]:
        """Liveness alias — same as /health."""
        return {
            "status": "ok",
            "application": application_name,
            "version": version,
        }

    if auth_dependency is not None:

        @router.get("/status", dependencies=[Depends(auth_dependency)])
        async def status() -> dict[str, Any]:
            """Full status with dependency checks (authenticated)."""
            results: dict[str, Any] = {}
            if checks:
                for name, check_fn in checks.items():
                    try:
                        results[name] = await check_fn()
                    except Exception as exc:
                        results[name] = {"status": "error", "message": str(exc)}

            return {
                "status": "ok",
                "application": application_name,
                "version": version,
                "env_file": env_file,
                "checks": results,
            }
    else:

        @router.get("/status")
        async def status_no_auth() -> dict[str, Any]:
            """Full status (no auth configured)."""
            results: dict[str, Any] = {}
            if checks:
                for name, check_fn in checks.items():
                    try:
                        results[name] = await check_fn()
                    except Exception as exc:
                        results[name] = {"status": "error", "message": str(exc)}

            return {
                "status": "ok",
                "application": application_name,
                "version": version,
                "env_file": env_file,
                "checks": results,
            }

    return router
