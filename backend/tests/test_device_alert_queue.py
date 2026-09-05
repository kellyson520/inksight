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


def test_device_alert_queue_has_per_device_and_global_bounds():
    from api.routes import device

    device._device_alerts.clear()
    now = datetime.now()
    for index in range(device._ALERT_QUEUE_LIMIT + 2):
        device.enqueue_device_alert("AA", {"message": str(index), "expires_at": now + timedelta(seconds=30)})
    assert len(device._device_alerts["AA"]) == device._ALERT_QUEUE_LIMIT
    assert device.pop_device_alert("AA", now=now)["message"] == "2"

    for index in range(device._ALERT_GLOBAL_KEY_LIMIT + 3):
        device.enqueue_device_alert(f"AA:{index:02X}", {"message": "x", "expires_at": now + timedelta(seconds=30)})
    assert len(device._device_alerts) <= device._ALERT_GLOBAL_KEY_LIMIT
