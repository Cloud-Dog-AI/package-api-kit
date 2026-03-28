# cloud-dog-api-kit

**Part of the [Cloud-Dog AI Platform](https://www.cloud-dog.ai)**

> Intelligent automation through composable AI agents, MCP servers, and shared platform services.

## About Cloud-Dog AI

Cloud-Dog AI is a platform of 10+ composable services for AI-powered business automation — natural language SQL queries, email management, file operations, git workflows, notification delivery, and expert knowledge retrieval. All services share a common set of platform packages for configuration, logging, authentication, job queues, LLM integration, vector databases, and caching.

This package provides: a FastAPI toolkit with standardised middleware, health checks, request logging, error handling, and OpenAPI generation.

## Installation

```bash
pip install cloud-dog-api-kit
```

Available from the [Cloud-Dog AI package registry](https://www.cloud-dog.ai/packages).

## Quick Start

```python
from cloud_dog_api_kit import *

# See API Reference below for available functions and classes
```

## API Reference

### Exports

```python
from cloud_dog_api_kit import (
    APIError,
    ConflictError,
    CorrelationMiddleware,
    ErrorDetail,
    ErrorResponse,
    GracefulShutdownManager,
    HealthCheck,
    InternalError,
    LegacyEnvelopeMiddleware,
    LegacyRouteAdapter,
    LegacyRouteAdapterMiddleware,
    LifecycleHooks,
    MCPContractRegistration,
    McpSessionManager,
    Meta,
    NotFoundError,
    PageInfo,
    PaginatedData,
    ProfileContextMiddleware,
    RateLimitError,
    RequestLoggingMiddleware,
    RequestSizeLimitMiddleware,
    ShutdownDrainMiddleware,
    SuccessResponse,
    TimeoutError,
    ToolContract,
    UnauthenticatedError,
    UnauthorisedError,
    UpstreamError,
    ValidationError,
    VersionHeaderMiddleware,
    WebhookSignatureMiddleware,
    annotations,
    compute_webhook_signature,
    configure_cors,
    configure_openapi,
    create_app,
    create_health_router,
    error_envelope,
    install_shutdown_signal_handlers,
    legacy_envelope_route,
    map_legacy_mcp_payload,
    paginated_envelope,
    register_error_handlers,
    register_mcp_contract,
    register_mcp_routes,
    register_tool_router,
    success_envelope,
)
```

## Dependencies

- `fastapi>=0.110`
- `starlette>=0.36`
- `pydantic>=2.0`
- `httpx>=0.27`

## Testing

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run unit tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=cloud_dog_api_kit --cov-report=term-missing
```

### Test Structure
- `tests/unit/` — Unit tests (no external dependencies)
- `tests/integration/` — Integration tests (requires running services)

## Related Packages

| Package | Description |
|---------|-------------|
| cloud-dog-config | Layered configuration with Vault integration |
| cloud-dog-logging | Structured JSON logging with correlation IDs |
| cloud-dog-api-kit | FastAPI toolkit with middleware and routing |
| cloud-dog-idam | Identity and access management client |
| cloud-dog-jobs | Background job scheduling and execution |
| cloud-dog-llm | LLM client abstraction (OpenAI, Ollama, etc.) |
| cloud-dog-vdb | Vector database client (Infinity, pgvector) |
| cloud-dog-cache | Caching abstraction with Redis/Valkey support |
| cloud-dog-tokens | Design tokens for UI consistency |
| cloud-dog-ui | React component library |
| cloud-dog-shell | Application shell and navigation |
| cloud-dog-auth | Frontend authentication flows |
| cloud-dog-api-client | TypeScript API client |
| cloud-dog-config-fe | Frontend configuration management |
| cloud-dog-testing | Test utilities and fixtures |

## Version

0.2.0

---

## Licence

Apache 2.0

Copyright 2026 [Cloud-Dog](https://www.cloud-dog.ai), Viewdeck Engineering Limited ([viewdeck.io](https://www.viewdeck.io))

[info@cloud-dog.ai](mailto:info@cloud-dog.ai)
