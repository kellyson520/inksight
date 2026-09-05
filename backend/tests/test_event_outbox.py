from __future__ import annotations

from core.event_outbox import EventOutbox


def test_outbox_deduplicates_events_by_idempotency_key(tmp_path):
    outbox = EventOutbox(tmp_path / "events.json")
    event = {"event_id": "hotlist:zhihu:a:new", "kind": "new", "item_id": "a"}

    assert outbox.publish(event) is True
    assert outbox.publish(event) is False
    assert outbox.list_pending()[0]["event_id"] == event["event_id"]


def test_outbox_ack_removes_event_and_survives_reload(tmp_path):
    path = tmp_path / "events.json"
    outbox = EventOutbox(path)
    event = {"event_id": "monitor:1", "kind": "changed"}
    outbox.publish(event)

    reloaded = EventOutbox(path)
    assert reloaded.list_pending()[0]["event_id"] == event["event_id"]
    assert reloaded.ack("monitor:1") is True
    assert reloaded.list_pending() == []


def test_outbox_quarantines_corrupt_file_instead_of_overwriting(tmp_path):
    path = tmp_path / "events.json"
    path.write_text("{broken", encoding="utf-8")
    outbox = EventOutbox(path)

    assert outbox.list_pending() == []
    assert list(tmp_path.glob("events.json.corrupt-*"))


def test_outbox_instances_do_not_overwrite_each_other(tmp_path):
    path = tmp_path / "events.json"
    first = EventOutbox(path)
    second = EventOutbox(path)

    assert first.publish({"event_id": "first", "kind": "new"}) is True
    assert second.publish({"event_id": "second", "kind": "new"}) is True
    assert {event["event_id"] for event in EventOutbox(path).list_pending()} == {"first", "second"}
