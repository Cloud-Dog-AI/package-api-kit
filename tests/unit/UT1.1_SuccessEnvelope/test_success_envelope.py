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

"""UT1.1: Success Envelope — schema validation tests."""

from __future__ import annotations
from cloud_dog_api_kit.envelopes.success import Meta, SuccessResponse, success_envelope


class TestSuccessEnvelope:
    def test_ok_is_true(self) -> None:
        resp = SuccessResponse(data={"key": "value"})
        assert resp.ok is True

    def test_data_field_present(self) -> None:
        resp = SuccessResponse(data={"items": [1, 2]})
        assert resp.data == {"items": [1, 2]}

    def test_meta_default(self) -> None:
        resp = SuccessResponse(data={})
        assert isinstance(resp.meta, Meta)

    def test_meta_request_id(self) -> None:
        resp = SuccessResponse(data={}, meta=Meta(request_id="req-001"))
        assert resp.meta.request_id == "req-001"

    def test_meta_version(self) -> None:
        resp = SuccessResponse(data={}, meta=Meta(version="v2"))
        assert resp.meta.version == "v2"

    def test_success_envelope_helper(self) -> None:
        result = success_envelope(data={"id": "1"}, request_id="r-1", version="v1")
        assert result["ok"] is True
        assert result["data"]["id"] == "1"
        assert result["meta"]["request_id"] == "r-1"

    def test_json_serialisation_roundtrip(self) -> None:
        resp = SuccessResponse(data={"name": "test"}, meta=Meta(request_id="r-2"))
        d = resp.model_dump()
        assert d["ok"] is True
        assert d["data"]["name"] == "test"
        assert d["meta"]["request_id"] == "r-2"
