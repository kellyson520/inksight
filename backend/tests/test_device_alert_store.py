from datetime import datetime, timedelta

import pytest

from core.device_alert_store import DeviceAlertQueue


@pytest.mark.asyncio
async def test_alert_queue_is_shared_across_instances(tmp_path):
    path = tmp_path / "alerts.sqlite"
    producer = DeviceAlertQueue(path, per_device_limit=2)
    consumer = DeviceAlertQueue(path, per_device_limit=2)
    now = datetime.now()
    await producer.enqueue("AA:BB", {"message": "one", "expires_at": (now + timedelta(seconds=30)).isoformat()})
    await producer.enqueue("AA:BB", {"message": "two", "expires_at": (now + timedelta(seconds=30)).isoformat()})

    assert (await consumer.pop("AA:BB", now=now))["message"] == "one"
    assert (await consumer.pop("AA:BB", now=now))["message"] == "two"
    assert await consumer.pop("AA:BB", now=now) is None


@pytest.mark.asyncio
async def test_alert_queue_evicts_oldest_when_limit_exceeded(tmp_path):
    queue = DeviceAlertQueue(tmp_path / "alerts.sqlite", per_device_limit=2)
    now = datetime.now()
    for message in ("one", "two", "three"):
        await queue.enqueue("AA:BB", {"message": message, "expires_at": (now + timedelta(seconds=30)).isoformat()})
    assert (await queue.pop("AA:BB", now=now))["message"] == "two"
    assert (await queue.pop("AA:BB", now=now))["message"] == "three"
