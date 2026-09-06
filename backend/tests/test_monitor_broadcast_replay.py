import hashlib
import hmac
import time
from unittest.mock import patch

import pytest



def _signature(secret, timestamp, nonce, payload):
    body = f"{timestamp}.{nonce}.{payload.model_dump_json()}".encode()
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


@pytest.mark.asyncio
async def test_broadcast_requires_fresh_timestamp_and_nonce(monkeypatch, tmp_path):
    import api.routes.monitors as monitors
    from api.routes.monitors import EventPushSchema, push_event

    monitors._MONITOR_NONCE_STORE = __import__("core.monitor_nonce_store", fromlist=["MonitorNonceStore"]).MonitorNonceStore(tmp_path / "nonces.sqlite")
    monkeypatch.setenv("MONITOR_WEBHOOK_SECRET", "secret")
    payload = EventPushSchema(site_name="x", new_snippet="changed", target_mac="*")
    timestamp = str(int(time.time()))
    nonce = "nonce-1"
    signature = _signature("secret", timestamp, nonce, payload)
    with patch("api.routes.monitors.monitor_service.create_change_notice", return_value={"id": "n"}):
        result = await push_event(payload, None, None, None, timestamp, nonce, signature)
    assert result["success"] is True


@pytest.mark.asyncio
async def test_broadcast_rejects_expired_and_replayed_nonce(monkeypatch, tmp_path):
    import api.routes.monitors as monitors
    from api.routes.monitors import EventPushSchema, push_event

    monitors._MONITOR_NONCE_STORE = __import__("core.monitor_nonce_store", fromlist=["MonitorNonceStore"]).MonitorNonceStore(tmp_path / "nonces.sqlite")
    monkeypatch.setenv("MONITOR_WEBHOOK_SECRET", "secret")
    payload = EventPushSchema(site_name="x", new_snippet="changed", target_mac="*")
    timestamp = str(int(time.time()))
    nonce = "replay-1"
    signature = _signature("secret", timestamp, nonce, payload)
    with patch("api.routes.monitors.monitor_service.create_change_notice", return_value={"id": "n"}):
        await push_event(payload, None, None, None, timestamp, nonce, signature)
        with pytest.raises(Exception) as error:
            await push_event(payload, None, None, None, timestamp, nonce, signature)
    assert error.value.status_code == 403


@pytest.mark.asyncio
async def test_broadcast_nonce_replay_is_rejected_after_store_reload(monkeypatch, tmp_path):
    import api.routes.monitors as monitors
    from api.routes.monitors import EventPushSchema, push_event
    from core.monitor_nonce_store import MonitorNonceStore

    monkeypatch.setenv("MONITOR_WEBHOOK_SECRET", "secret")
    monitors._MONITOR_NONCE_STORE = MonitorNonceStore(tmp_path / "nonces.sqlite")
    payload = EventPushSchema(site_name="x", new_snippet="changed", target_mac="*")
    timestamp = str(int(time.time()))
    nonce = "reload-replay"
    signature = _signature("secret", timestamp, nonce, payload)
    with patch("api.routes.monitors.monitor_service.create_change_notice", return_value={"id": "n"}):
        await push_event(payload, None, None, None, timestamp, nonce, signature)
        monitors._MONITOR_NONCE_STORE = MonitorNonceStore(tmp_path / "nonces.sqlite")
        with pytest.raises(Exception) as error:
            await push_event(payload, None, None, None, timestamp, nonce, signature)
    assert error.value.status_code == 403
