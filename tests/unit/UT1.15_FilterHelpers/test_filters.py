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

"""UT1.15: Filter Helpers — sort and filter parsing tests."""

from __future__ import annotations
from cloud_dog_api_kit.schemas.filters import parse_sort, parse_filters


class TestFilterHelpers:
    def test_parse_sort_none(self) -> None:
        f, d = parse_sort(None)
        assert f is None and d == "asc"

    def test_parse_sort_field_only(self) -> None:
        f, d = parse_sort("name")
        assert f == "name" and d == "asc"

    def test_parse_sort_with_desc(self) -> None:
        f, d = parse_sort("created_at:desc")
        assert f == "created_at" and d == "desc"

    def test_parse_sort_with_asc(self) -> None:
        f, d = parse_sort("name:asc")
        assert f == "name" and d == "asc"

    def test_parse_filters_excludes_pagination(self) -> None:
        result = parse_filters({"offset": "0", "limit": "10", "sort": "name", "status": "active"})
        assert result == {"status": "active"}

    def test_parse_filters_allowed_fields(self) -> None:
        result = parse_filters({"status": "active", "type": "user", "hack": "x"}, allowed_fields=["status", "type"])
        assert result == {"status": "active", "type": "user"}

    def test_parse_filters_no_allowed(self) -> None:
        result = parse_filters({"status": "active", "type": "user"})
        assert result == {"status": "active", "type": "user"}

    def test_parse_filters_empty(self) -> None:
        result = parse_filters({})
        assert result == {}
