from __future__ import annotations

import pytest

from core.event_delivery import DeviceEventDeliveryAdapter


@pytest.mark.asyncio
async def test_device_adapter_delivers_hotlist_event_to_target_device():
    calls = []

    class Push:
        async def push_to_device(self, **kwargs):
            calls.append(kwargs)
            return True

    adapter = DeviceEventDeliveryAdapter(Push())
    assert await adapter.publish({
        "event_id": "hotlist:zhihu:a:new:0:1",
        "kind": "new",
        "platform": "zhihu",
        "item_id": "a",
        "rank": 1,
        "target_mac": "AA:BB",
    }) is True
    assert calls[0]["mac"] == "AA:BB"
    assert calls[0]["sender"] == "HOTLIST"


@pytest.mark.asyncio
async def test_device_adapter_does_not_deliver_non_realtime_events():
    class Push:
        async def push_to_device(self, **kwargs):
            raise AssertionError("must not push")

    adapter = DeviceEventDeliveryAdapter(Push())
    assert await adapter.publish({"event_id": "e", "is_realtime": False, "target_mac": "AA"}) is True


@pytest.mark.asyncio
async def test_device_adapter_retains_event_without_target_device():
    adapter = DeviceEventDeliveryAdapter(object())
    assert await adapter.publish({"event_id": "e", "is_realtime": True}) is False
