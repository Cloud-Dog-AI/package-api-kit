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

# cloud_dog_api_kit — FastAPI application factory
#
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: `create_app()` wires standard middleware, error handlers,
#   health routes, and version endpoint for Cloud-Dog services.
# Related requirements: FR10.4, FR12.1, FR6.1
# Related architecture: SA1

"""FastAPI application factory for cloud_dog_api_kit."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any, Callable

from fastapi import FastAPI

from cloud_dog_api_kit.correlation import CorrelationMiddleware
from cloud_dog_api_kit.errors import register_error_handlers
from cloud_dog_api_kit.lifecycle import (
    GracefulShutdownManager,
    LifecycleHooks,
    ShutdownDrainMiddleware,
    install_shutdown_signal_handlers,
)
from cloud_dog_api_kit.middleware import RequestLoggingMiddleware, TimingMiddleware, TimeoutMiddleware, configure_cors
from cloud_dog_api_kit.middleware.request_size_limit import RequestSizeLimitMiddleware
from cloud_dog_api_kit.routers.health import create_health_router
from cloud_dog_api_kit.versioning import VersionHeaderMiddleware


def create_app(
    title: str,
    version: str = "0.0.0",
    description: str = "",
    api_prefix: str = "/api/v1",
    base_path: str = "",
    health_checks: dict[str, Callable] | None = None,
    auth_verify_fn: Callable | None = None,
    enable_request_logging: bool = True,
    enable_cors: bool = True,
    cors_origins: list[str] | None = None,
    enable_docs: bool = True,
    enable_streaming: bool = False,
    lifecycle_hooks: LifecycleHooks | None = None,
    enable_health: bool = True,
    max_request_body_bytes: int | None = None,
    timeout_seconds: float = 30.0,
    shutdown_drain_timeout_seconds: float = 5.0,
    register_signal_handlers_on_startup: bool = True,
) -> FastAPI:
    """Create a fully configured FastAPI application.

    Wires:
    - Error handlers (APIError, validation, unhandled)
    - Correlation ID middleware (X-Request-Id, X-Correlation-Id, X-App-Id)
    - Request logging middleware
    - CORS middleware (production-safe defaults)
    - Health/ready/live/status routes
    - /api/v1/version endpoint
    - X-API-Version response header
    - Swagger UI / ReDoc (disableable)
    - Reverse proxy base path via ``root_path`` (DC-11)

    Args:
        base_path: URL prefix when behind a reverse proxy (e.g. "/api").
            Passed as FastAPI ``root_path`` so generated URLs, OpenAPI docs,
            and redirects include the prefix. Default "" (no prefix).
    """
    hooks = lifecycle_hooks or LifecycleHooks()
    shutdown_manager = GracefulShutdownManager(drain_timeout_seconds=shutdown_drain_timeout_seconds)

    @asynccontextmanager
    async def _lifespan(app: FastAPI):
        await hooks.run_startup(app)
        if register_signal_handlers_on_startup:
            install_shutdown_signal_handlers(shutdown_manager)
        try:
            yield
        finally:
            await shutdown_manager.initiate_shutdown()
            await hooks.run_shutdown(app)

    app = FastAPI(
        title=title,
        version=version,
        description=description,
        root_path=base_path,
        docs_url="/docs" if enable_docs else None,
        redoc_url="/redoc" if enable_docs else None,
        lifespan=_lifespan,
    )
    app.state.lifecycle_hooks = hooks
    app.state.shutdown_manager = shutdown_manager

    register_error_handlers(app)

    # Middleware ordering: outermost first.
    app.add_middleware(VersionHeaderMiddleware, version="v1")
    if enable_request_logging:
        app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(TimingMiddleware)
    app.add_middleware(TimeoutMiddleware, timeout_seconds=timeout_seconds)
    if max_request_body_bytes is not None:
        app.add_middleware(RequestSizeLimitMiddleware, max_bytes=max_request_body_bytes)
    app.add_middleware(ShutdownDrainMiddleware, manager=shutdown_manager)
    app.add_middleware(CorrelationMiddleware)
    if enable_cors:
        configure_cors(app, allowed_origins=cors_origins)

    # Health routes. /status can be protected if a verify function is supplied.
    # Set enable_health=False when the project defines its own custom health endpoints.
    if enable_health:
        from cloud_dog_api_kit.auth.dependency import create_auth_dependency

        auth_dep = None
        if auth_verify_fn:
            auth_dep = create_auth_dependency(api_key_verify_fn=auth_verify_fn)

        app.include_router(
            create_health_router(
                application_name=title,
                version=version,
                checks=health_checks,
                auth_dependency=auth_dep,
            )
        )

    @app.get(f"{api_prefix}/version", tags=["system"])
    async def api_version() -> dict[str, Any]:
        """Return the API version information."""
        return {
            "application": title,
            "version": version,
            "api_version": "v1",
        }

    return app
