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

# cloud_dog_api_kit — A2A gateway helpers
#
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Helpers for mapping REST endpoints to A2A handlers.
#   A2A endpoints MUST be thin wrappers over REST calls.
# Related requirements: FR15.1
# Related architecture: CC1.18

"""A2A gateway helpers for cloud_dog_api_kit."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class A2AHandler:
    """A2A handler definition mapped from a REST endpoint.

    Attributes:
        name: The handler name.
        description: Human-readable description.
        endpoint_path: The REST endpoint path this handler wraps.
        method: HTTP method. Defaults to ``POST``.
        input_schema: JSON Schema for the handler's input.
        output_schema: JSON Schema for the handler's output.

    Related tests: UT1.33_A2AGateway
    """

    name: str
    description: str
    endpoint_path: str
    method: str = "POST"
    input_schema: dict[str, Any] = field(default_factory=dict)
    output_schema: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to a dictionary suitable for A2A registration.

        Returns:
            A dictionary with the handler definition.
        """
        return {
            "name": self.name,
            "description": self.description,
            "endpoint_path": self.endpoint_path,
            "method": self.method,
            "inputSchema": self.input_schema,
            "outputSchema": self.output_schema,
        }


def create_a2a_handler_from_endpoint(
    endpoint_path: str,
    method: str = "POST",
    description: str = "",
    name: str | None = None,
    input_schema: dict[str, Any] | None = None,
    output_schema: dict[str, Any] | None = None,
) -> A2AHandler:
    """Create an A2A handler from a REST endpoint.

    Args:
        endpoint_path: The REST endpoint path.
        method: HTTP method. Defaults to ``POST``.
        description: Handler description.
        name: Override handler name. Derived from path if None.
        input_schema: JSON Schema for inputs.
        output_schema: JSON Schema for outputs.

    Returns:
        An A2AHandler instance.

    Related tests: UT1.33_A2AGateway
    """
    if name is None:
        parts = endpoint_path.strip("/").split("/")
        filtered = [p for p in parts if not p.startswith("{") and p not in ("api", "v1", "v2")]
        name = "_".join(filtered).replace(":", "_")

    return A2AHandler(
        name=name,
        description=description,
        endpoint_path=endpoint_path,
        method=method,
        input_schema=input_schema or {},
        output_schema=output_schema or {},
    )
