import hashlib
import hmac
import time
from unittest.mock import patch

import pytest
from fastapi import HTTPException


def _signature(secret, timestamp, nonce, payload):
    body = f"{timestamp}.{nonce}.{payload.model_dump_json()}".encode()
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


@pytest.mark.asyncio
async def test_broadcast_requires_fresh_timestamp_and_nonce(monkeypatch):
    from api.routes.monitors import EventPushSchema, push_event

    monkeypatch.setenv("MONITOR_WEBHOOK_SECRET", "secret")
    payload = EventPushSchema(site_name="x", new_snippet="changed", target_mac="*")
    timestamp = str(int(time.time()))
    nonce = "nonce-1"
    signature = _signature("secret", timestamp, nonce, payload)
    with patch("api.routes.monitors.monitor_service.create_change_notice", return_value={"notice_id": "n"}):
        result = await push_event(payload, None, None, None, timestamp, nonce, signature)
    assert result["success"] is True


@pytest.mark.asyncio
async def test_broadcast_rejects_expired_and_replayed_nonce(monkeypatch):
    from api.routes.monitors import EventPushSchema, push_event

    monkeypatch.setenv("MONITOR_WEBHOOK_SECRET", "secret")
    payload = EventPushSchema(site_name="x", new_snippet="changed", target_mac="*")
    old_timestamp = str(int(time.time()) - 301)
    with pytest.raises(HTTPException) as expired:
        await push_event(payload, None, None, old_timestamp, "old", _signature("secret", old_timestamp, "old", payload))
    assert expired.value.status_code == 403

    timestamp = str(int(time.time()))
    nonce = "replay-1"
    signature = _signature("secret", timestamp, nonce, payload)
    with patch("api.routes.monitors.monitor_service.create_change_notice", return_value={"notice_id": "n"}):
        await push_event(payload, None, None, None, timestamp, nonce, signature)
        with pytest.raises(HTTPException) as replayed:
            await push_event(payload, None, None, None, timestamp, nonce, signature)
    assert replayed.value.status_code == 403
