# Build Instructions

## Package
`cloud-dog-api-kit` - shared API server primitives, middleware, and HTTP tooling.

## Prerequisites
- Python 3.11+
- pip

## Development Setup
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip build twine
pip install -e ".[dev]"
```

If your environment resolves dependencies from an additional package index:
```bash
PYPI_URL=https://packages.example.com/simple/
pip install -e ".[dev]" --extra-index-url "$PYPI_URL"
```

## Local Use
Install the package in editable mode and import it from an interactive shell or another local project:
```bash
python -c "import cloud_dog_api_kit; print('package import ok')"
```

## Run Tests
```bash
ruff check cloud_dog_api_kit tests examples
ruff format --check cloud_dog_api_kit tests examples
python -m pytest tests/quality --env tests/env-UT -v
python -m pytest tests/unit --env tests/env-UT -v
python -m pytest tests/system --env tests/env-UT -v
python -m pytest tests/integration --env tests/env-UT -v
python -m pytest tests/application --env tests/env-UT -v
python -m pytest tests/security --env tests/env-UT -v
```

## Build Distribution
```bash
python -m build
```

## Publish
```bash
twine upload --repository-url "$PYPI_URL" dist/*
```

## Docker Packaging
If you consume this package during a container build, pass the package index via environment variables:
```bash
PYPI_URL=https://packages.example.com/simple/ \
PYPI_USERNAME=build-user \
PYPI_PASSWORD=build-password \
docker build -t cloud-dog-api-kit:latest .
```

## Dependencies
- core runtime dependencies include `fastapi`, `starlette`, `pydantic`, and `httpx`

## Configuration
Tests and sample programs can read configuration from shell variables, a local env file, and package defaults where available.

## Vault Integration
Optional secret-backed test runs can load settings from a standard Vault client configuration:
```bash
export VAULT_ADDR=https://vault.example.com
export VAULT_TOKEN=your-token
export VAULT_MOUNT_POINT=your-mount
export VAULT_CONFIG_PATH=your-path
```
