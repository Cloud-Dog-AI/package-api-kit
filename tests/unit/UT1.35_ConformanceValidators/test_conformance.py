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

"""UT1.35: Conformance Validators — envelope validation tests."""

from __future__ import annotations
from cloud_dog_api_kit.testing.conformance import (
    validate_success_envelope,
    validate_error_envelope,
    validate_pagination_response,
    validate_correlation_id,
)


class TestConformanceValidators:
    def test_valid_success_envelope(self) -> None:
        resp = {"ok": True, "data": {"id": "1"}, "meta": {"request_id": "r-1"}}
        assert validate_success_envelope(resp) == []

    def test_missing_data_field(self) -> None:
        resp = {"ok": True, "meta": {"request_id": "r-1"}}
        errors = validate_success_envelope(resp)
        assert any("data" in e for e in errors)

    def test_missing_meta_field(self) -> None:
        resp = {"ok": True, "data": {}}
        errors = validate_success_envelope(resp)
        assert any("meta" in e for e in errors)

    def test_valid_error_envelope(self) -> None:
        resp = {"ok": False, "error": {"code": "NOT_FOUND", "message": "x", "retryable": False}, "meta": {}}
        assert validate_error_envelope(resp) == []

    def test_missing_error_code(self) -> None:
        resp = {"ok": False, "error": {"message": "x", "retryable": False}, "meta": {}}
        errors = validate_error_envelope(resp)
        assert any("code" in e for e in errors)

    def test_valid_pagination(self) -> None:
        resp = {
            "ok": True,
            "data": {"items": [], "page": {"limit": 10, "offset": 0, "has_more": False}},
            "meta": {"request_id": "r-1"},
        }
        assert validate_pagination_response(resp) == []

    def test_missing_items(self) -> None:
        resp = {
            "ok": True,
            "data": {"page": {"limit": 10, "offset": 0, "has_more": False}},
            "meta": {"request_id": "r-1"},
        }
        errors = validate_pagination_response(resp)
        assert any("items" in e for e in errors)

    def test_correlation_id_present(self) -> None:
        assert validate_correlation_id({"X-Request-Id": "abc"}) == []

    def test_correlation_id_missing(self) -> None:
        errors = validate_correlation_id({})
        assert len(errors) > 0
