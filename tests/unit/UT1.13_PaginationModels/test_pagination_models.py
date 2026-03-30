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

"""UT1.13: Pagination Models — PageInfo and PaginatedData tests."""

from __future__ import annotations
from cloud_dog_api_kit.schemas.pagination import PageInfo, PaginatedData, paginated_envelope


class TestPaginationModels:
    def test_page_info_fields(self) -> None:
        p = PageInfo(limit=50, offset=0, total=100, has_more=True)
        assert p.limit == 50
        assert p.offset == 0
        assert p.total == 100
        assert p.has_more is True

    def test_page_info_cursor(self) -> None:
        p = PageInfo(limit=10, offset=0, has_more=True, cursor="abc123")
        assert p.cursor == "abc123"

    def test_paginated_data(self) -> None:
        pd = PaginatedData(items=[{"id": "1"}], page=PageInfo(limit=10, offset=0, has_more=False))
        assert len(pd.items) == 1
        assert pd.page.has_more is False

    def test_paginated_envelope_helper(self) -> None:
        result = paginated_envelope(items=[1, 2], limit=10, offset=0, total=2, has_more=False, request_id="r-1")
        assert result["ok"] is True
        assert result["data"]["items"] == [1, 2]
        assert result["data"]["page"]["limit"] == 10
        assert result["data"]["page"]["total"] == 2
        assert result["meta"]["request_id"] == "r-1"

    def test_paginated_envelope_has_more(self) -> None:
        result = paginated_envelope(items=[1], limit=1, offset=0, total=5, has_more=True)
        assert result["data"]["page"]["has_more"] is True
