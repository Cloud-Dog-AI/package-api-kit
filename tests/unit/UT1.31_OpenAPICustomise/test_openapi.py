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

"""UT1.31: OpenAPI Customise — OpenAPI schema customisation tests."""

from __future__ import annotations
import pytest
from fastapi import FastAPI
from cloud_dog_api_kit.openapi.customise import configure_openapi


@pytest.mark.asyncio
class TestOpenAPICustomise:
    async def test_tags_applied(self) -> None:
        app = FastAPI(title="Test")
        configure_openapi(app, tags=[{"name": "users", "description": "User ops"}])
        assert app.openapi_tags == [{"name": "users", "description": "User ops"}]

    async def test_security_schemes_applied(self) -> None:
        app = FastAPI(title="Test")

        @app.get("/test")
        async def t():
            return {}

        configure_openapi(app, security_schemes={"ApiKeyAuth": {"type": "apiKey", "in": "header", "name": "X-API-Key"}})
        schema = app.openapi()
        assert "securitySchemes" in schema["components"]
        assert "ApiKeyAuth" in schema["components"]["securitySchemes"]
