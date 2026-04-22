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

"""UT1.11: Correlation Context — contextvars management tests."""

from __future__ import annotations
from cloud_dog_api_kit.correlation.context import (
    get_request_id,
    set_request_id,
    get_correlation_id,
    set_correlation_id,
    get_app_id,
    set_app_id,
    get_host_id,
    set_host_id,
    clear_context,
)


class TestCorrelationContext:
    def test_request_id_auto_generated(self) -> None:
        clear_context()
        rid = get_request_id()
        assert rid is not None and len(rid) == 32

    def test_set_and_get_request_id(self) -> None:
        set_request_id("my-req-id")
        assert get_request_id() == "my-req-id"

    def test_correlation_id_none_by_default(self) -> None:
        clear_context()
        assert get_correlation_id() is None

    def test_set_and_get_correlation_id(self) -> None:
        set_correlation_id("corr-123")
        assert get_correlation_id() == "corr-123"

    def test_app_id_none_by_default(self) -> None:
        clear_context()
        assert get_app_id() is None

    def test_set_and_get_app_id(self) -> None:
        set_app_id("expert-agent")
        assert get_app_id() == "expert-agent"

    def test_host_id_none_by_default(self) -> None:
        clear_context()
        assert get_host_id() is None

    def test_set_and_get_host_id(self) -> None:
        set_host_id("host-001")
        assert get_host_id() == "host-001"

    def test_clear_resets_all(self) -> None:
        set_request_id("r")
        set_correlation_id("c")
        set_app_id("a")
        set_host_id("h")
        clear_context()
        assert get_correlation_id() is None
        assert get_app_id() is None
        assert get_host_id() is None
