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

"""UT1.33: A2A Gateway — A2A handler definition mapping tests."""

from __future__ import annotations
from cloud_dog_api_kit.a2a.gateway import A2AHandler, create_a2a_handler_from_endpoint


class TestA2AGateway:
    def test_create_handler_from_endpoint(self) -> None:
        h = create_a2a_handler_from_endpoint("/api/v1/notify", description="Send notification")
        assert h.name == "notify"
        assert h.endpoint_path == "/api/v1/notify"

    def test_custom_name(self) -> None:
        h = create_a2a_handler_from_endpoint("/api/v1/jobs", name="submit_job")
        assert h.name == "submit_job"

    def test_to_dict(self) -> None:
        h = A2AHandler(name="test", description="Test", endpoint_path="/test", input_schema={"type": "object"})
        d = h.to_dict()
        assert d["name"] == "test"
        assert d["inputSchema"] == {"type": "object"}

    def test_derived_name_strips_version(self) -> None:
        h = create_a2a_handler_from_endpoint("/api/v1/deliveries")
        assert h.name == "deliveries"
