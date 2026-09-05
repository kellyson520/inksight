from datetime import datetime, timedelta


def test_device_alert_queue_preserves_fifo_and_drops_expired():
    from api.routes import device

    device._device_alerts.clear()
    now = datetime.now()
    device.enqueue_device_alert("AA", {"sender": "one", "message": "1", "expires_at": now + timedelta(seconds=30)})
    device.enqueue_device_alert("AA", {"sender": "two", "message": "2", "expires_at": now + timedelta(seconds=30)})
    device.enqueue_device_alert("AA", {"sender": "old", "message": "0", "expires_at": now - timedelta(seconds=1)})

    first = device.pop_device_alert("AA", now=now)
    second = device.pop_device_alert("AA", now=now)
    assert first["message"] == "1"
    assert second["message"] == "2"
    assert device.pop_device_alert("AA", now=now) is None
