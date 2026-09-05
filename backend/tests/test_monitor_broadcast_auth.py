from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException


@pytest.mark.asyncio
async def test_monitor_broadcast_requires_signed_internal_request():
    from api.routes.monitors import EventPushSchema, push_event

    payload = EventPushSchema(site_name="x", new_snippet="changed", target_mac="*")
    with pytest.raises(HTTPException) as error:
        await push_event(payload, None, None, None, None)
    assert error.value.status_code == 403


@pytest.mark.asyncio
async def test_monitor_broadcast_rejects_invalid_signature(monkeypatch):
    from api.routes.monitors import EventPushSchema, push_event

    monkeypatch.setenv("MONITOR_WEBHOOK_SECRET", "test-secret")
    payload = EventPushSchema(site_name="x", new_snippet="changed", target_mac="*")
    with pytest.raises(Exception) as error:
        await push_event(payload, None, None, None, "bad")
    assert error.value.status_code == 403


@pytest.mark.asyncio
async def test_monitor_broadcast_accepts_valid_signature(monkeypatch):
    import hashlib
    import hmac
    from api.routes.monitors import EventPushSchema, push_event

    secret = "test-secret"
    monkeypatch.setenv("MONITOR_WEBHOOK_SECRET", secret)
    payload = EventPushSchema(site_name="x", new_snippet="changed", target_mac="*")
    body = payload.model_dump_json().encode()
    signature = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    with patch("api.routes.monitors.monitor_service.create_change_notice", return_value={"notice_id": "n"}):
        result = await push_event(payload, None, None, None, signature)
    assert result["success"] is True
