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

"""UT1.43: HMAC signature, timestamp validation, and replay detection."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from cloud_dog_api_kit.webhook import WebhookSignatureMiddleware, compute_webhook_signature


@pytest.mark.asyncio
class TestWebhookSignatureVerification:
    async def test_valid_signature_passes(self) -> None:
        app = FastAPI()
        app.add_middleware(
            WebhookSignatureMiddleware,
            secret="secret",
            protected_paths={"/webhook"},
            clock=lambda: 1000,
            tolerance_seconds=300,
        )

        @app.post("/webhook")
        async def webhook() -> dict:
            return {"ok": True}

        body = b'{"event":"created"}'
        signature = compute_webhook_signature("secret", 1000, body)
        headers = {"X-Timestamp": "1000", "X-Signature": signature, "Content-Type": "application/json"}

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
            response = await client.post("/webhook", content=body, headers=headers)

        assert response.status_code == 200
        assert response.json()["ok"] is True

    async def test_invalid_signature_rejected(self) -> None:
        app = FastAPI()
        app.add_middleware(
            WebhookSignatureMiddleware,
            secret="secret",
            protected_paths={"/webhook"},
            clock=lambda: 1000,
            tolerance_seconds=300,
        )

        @app.post("/webhook")
        async def webhook() -> dict:
            return {"ok": True}

        headers = {"X-Timestamp": "1000", "X-Signature": "bad", "Content-Type": "application/json"}
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
            response = await client.post("/webhook", content=b"{}", headers=headers)

        assert response.status_code == 401
        assert response.json()["error"]["code"] == "UNAUTHENTICATED"

    async def test_expired_timestamp_and_replay_rejected(self) -> None:
        app = FastAPI()
        app.add_middleware(
            WebhookSignatureMiddleware,
            secret="secret",
            protected_paths={"/webhook"},
            clock=lambda: 1000,
            tolerance_seconds=10,
            replay_ttl_seconds=60,
        )

        @app.post("/webhook")
        async def webhook() -> dict:
            return {"ok": True}

        body = b'{"event":"updated"}'
        valid_signature = compute_webhook_signature("secret", 1000, body)
        replay_headers = {"X-Timestamp": "1000", "X-Signature": valid_signature, "Content-Type": "application/json"}

        expired_signature = compute_webhook_signature("secret", 500, body)
        expired_headers = {"X-Timestamp": "500", "X-Signature": expired_signature, "Content-Type": "application/json"}

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
            first = await client.post("/webhook", content=body, headers=replay_headers)
            replay = await client.post("/webhook", content=body, headers=replay_headers)
            expired = await client.post("/webhook", content=body, headers=expired_headers)

        assert first.status_code == 200
        assert replay.status_code == 401
        assert expired.status_code == 401
