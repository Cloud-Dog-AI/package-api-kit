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

"""UT1.2: Error Envelope — schema validation tests."""

from __future__ import annotations
from cloud_dog_api_kit.envelopes.error import ErrorDetail, ErrorResponse, error_envelope
from cloud_dog_api_kit.envelopes.success import Meta


class TestErrorEnvelope:
    def test_ok_is_false(self) -> None:
        resp = ErrorResponse(error=ErrorDetail(code="NOT_FOUND", message="Not found"))
        assert resp.ok is False

    def test_error_code_present(self) -> None:
        resp = ErrorResponse(error=ErrorDetail(code="CONFLICT", message="Conflict"))
        assert resp.error.code == "CONFLICT"

    def test_retryable_field(self) -> None:
        resp = ErrorResponse(error=ErrorDetail(code="RATE_LIMITED", message="Slow down", retryable=True))
        assert resp.error.retryable is True

    def test_details_field_accepts_dict(self) -> None:
        resp = ErrorResponse(error=ErrorDetail(code="INVALID_REQUEST", message="Bad", details={"field": "reason"}))
        assert resp.error.details == {"field": "reason"}

    def test_meta_request_id(self) -> None:
        resp = ErrorResponse(error=ErrorDetail(code="X", message="X"), meta=Meta(request_id="r-1"))
        assert resp.meta.request_id == "r-1"

    def test_error_envelope_helper(self) -> None:
        result = error_envelope(code="NOT_FOUND", message="Not found", request_id="r-2", retryable=False)
        assert result["ok"] is False
        assert result["error"]["code"] == "NOT_FOUND"
        assert result["error"]["retryable"] is False
        assert result["meta"]["request_id"] == "r-2"

    def test_json_roundtrip(self) -> None:
        resp = ErrorResponse(error=ErrorDetail(code="INTERNAL_ERROR", message="Oops"))
        d = resp.model_dump()
        assert d["ok"] is False
        assert d["error"]["code"] == "INTERNAL_ERROR"
