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

"""UT1.24: Retry Policy — exponential backoff and jitter tests."""

from __future__ import annotations
from cloud_dog_api_kit.clients.http_client import RetryPolicy


class TestRetryPolicy:
    def test_defaults(self) -> None:
        p = RetryPolicy()
        assert p.max_retries == 3
        assert p.backoff_base == 0.5
        assert p.backoff_max == 30.0
        assert p.jitter is True
        assert 502 in p.retry_status_codes

    def test_delay_increases_exponentially(self) -> None:
        p = RetryPolicy(jitter=False, backoff_base=1.0)
        d0 = p.get_delay(0)
        d1 = p.get_delay(1)
        d2 = p.get_delay(2)
        assert d0 == 1.0
        assert d1 == 2.0
        assert d2 == 4.0

    def test_delay_capped_at_max(self) -> None:
        p = RetryPolicy(jitter=False, backoff_base=1.0, backoff_max=5.0)
        d10 = p.get_delay(10)
        assert d10 == 5.0

    def test_jitter_adds_variance(self) -> None:
        p = RetryPolicy(jitter=True, backoff_base=1.0)
        delays = {p.get_delay(0) for _ in range(20)}
        assert len(delays) > 1  # Should not all be identical

    def test_custom_retry_codes(self) -> None:
        p = RetryPolicy(retry_status_codes=(500, 503))
        assert 500 in p.retry_status_codes
        assert 502 not in p.retry_status_codes
