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

# cloud_dog_api_kit — Public API
#
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: PS-20 API toolkit for all Cloud-Dog Python services. Provides
#   standard envelopes, error taxonomy, auth, CRUD, pagination, health,
#   streaming, HTTP client, correlation, idempotency, CORS, timeout,
#   OpenAPI, MCP/A2A gateways, test scaffolding, and an app factory.
# Related requirements: SV1.1, SV1.2, FR17.1
# Related architecture: SA1

"""cloud_dog_api_kit — PS-20 API toolkit for Cloud-Dog services.

Public API:
    create_app(...)  — FastAPI app factory wiring all components.
"""

# ruff: noqa: E402

from __future__ import annotations


def create_app(*args, **kwargs):  # type: ignore[no-untyped-def]
    """Import the app factory lazily so optional dependencies remain optional."""
    try:
        from cloud_dog_api_kit.factory import create_app as _create_app
    except ModuleNotFoundError as exc:
        if exc.name != "cloud_dog_logging":
            raise
        raise ModuleNotFoundError("create_app requires the optional 'cloud-dog-logging' dependency") from exc
    return _create_app(*args, **kwargs)


from cloud_dog_api_kit.compat import (
    LegacyEnvelopeMiddleware,
    LegacyRouteAdapter,
    LegacyRouteAdapterMiddleware,
    ProfileContextMiddleware,
    legacy_envelope_route,
)
from cloud_dog_api_kit.correlation import CorrelationMiddleware
from cloud_dog_api_kit.middleware import configure_cors
from cloud_dog_api_kit.lifecycle import (
    GracefulShutdownManager,
    LifecycleHooks,
    ShutdownDrainMiddleware,
    install_shutdown_signal_handlers,
)
from cloud_dog_api_kit.mcp import (
    MCPContractRegistration,
    McpSessionManager,
    ToolContract,
    map_legacy_mcp_payload,
    register_mcp_contract,
    register_mcp_routes,
    register_tool_router,
)
from cloud_dog_api_kit.envelopes import (
    ErrorDetail,
    ErrorResponse,
    Meta,
    SuccessResponse,
    error_envelope,
    success_envelope,
)
from cloud_dog_api_kit.schemas.pagination import PageInfo, PaginatedData, paginated_envelope
from cloud_dog_api_kit.errors import (
    APIError,
    ConflictError,
    InternalError,
    NotFoundError,
    RateLimitError,
    TimeoutError,
    UnauthenticatedError,
    UnauthorisedError,
    UpstreamError,
    ValidationError,
    register_error_handlers,
)
from cloud_dog_api_kit.routers.health import HealthCheck, create_health_router
from cloud_dog_api_kit.middleware import RequestLoggingMiddleware, RequestSizeLimitMiddleware
from cloud_dog_api_kit.openapi import configure_openapi
from cloud_dog_api_kit.versioning import VersionHeaderMiddleware
from cloud_dog_api_kit.webhook import WebhookSignatureMiddleware, compute_webhook_signature
from cloud_dog_api_kit.web.proxy import WebApiProxy

__all__ = [
    "create_app",
    "APIError",
    "ConflictError",
    "InternalError",
    "NotFoundError",
    "RateLimitError",
    "TimeoutError",
    "UnauthenticatedError",
    "UnauthorisedError",
    "UpstreamError",
    "ValidationError",
    "GracefulShutdownManager",
    "ErrorDetail",
    "ErrorResponse",
    "LegacyEnvelopeMiddleware",
    "LegacyRouteAdapter",
    "LegacyRouteAdapterMiddleware",
    "LifecycleHooks",
    "MCPContractRegistration",
    "Meta",
    "McpSessionManager",
    "PageInfo",
    "PaginatedData",
    "ProfileContextMiddleware",
    "RequestSizeLimitMiddleware",
    "ShutdownDrainMiddleware",
    "SuccessResponse",
    "ToolContract",
    "WebhookSignatureMiddleware",
    "compute_webhook_signature",
    "error_envelope",
    "install_shutdown_signal_handlers",
    "legacy_envelope_route",
    "map_legacy_mcp_payload",
    "paginated_envelope",
    "register_mcp_contract",
    "register_mcp_routes",
    "success_envelope",
    "register_tool_router",
    "register_error_handlers",
    "HealthCheck",
    "create_health_router",
    "CorrelationMiddleware",
    "RequestLoggingMiddleware",
    "VersionHeaderMiddleware",
    "configure_cors",
    "configure_openapi",
    "WebApiProxy",
]
