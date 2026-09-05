from __future__ import annotations

import asyncio

from core.event_outbox import EventOutbox


def test_outbox_deduplicates_events_by_idempotency_key(tmp_path):
    outbox = EventOutbox(tmp_path / "events.json")
    event = {"event_id": "hotlist:zhihu:a:new", "kind": "new", "item_id": "a"}

    assert outbox.publish(event) is True
    assert outbox.publish(event) is False
    assert outbox.list_pending() == [event]


def test_outbox_ack_removes_event_and_survives_reload(tmp_path):
    path = tmp_path / "events.json"
    outbox = EventOutbox(path)
    event = {"event_id": "monitor:1", "kind": "changed"}
    outbox.publish(event)

    reloaded = EventOutbox(path)
    assert reloaded.list_pending() == [event]
    assert reloaded.ack("monitor:1") is True
    assert reloaded.list_pending() == []
