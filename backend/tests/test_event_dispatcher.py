from __future__ import annotations

import asyncio
import time

import pytest

from core.event_dispatcher import EventDispatcher
from core.event_outbox import EventOutbox


@pytest.mark.asyncio
async def test_dispatcher_acks_successful_events(tmp_path):
    outbox = EventOutbox(tmp_path / "events.json")
    outbox.publish({"event_id": "e1", "kind": "new"})
    seen = []

    async def publish(event):
        seen.append(event["event_id"])
        return True

    result = await EventDispatcher(outbox, publish=publish).dispatch_once()
    assert result == {"published": 1, "failed": 0, "expired": 0}
    assert seen == ["e1"]
    assert outbox.list_pending() == []


@pytest.mark.asyncio
async def test_dispatcher_keeps_failed_event_for_retry(tmp_path):
    outbox = EventOutbox(tmp_path / "events.json")
    outbox.publish({"event_id": "e1", "kind": "new"})

    async def publish(_event):
        return False

    result = await EventDispatcher(outbox, publish=publish, max_attempts=2, backoff=0).dispatch_once()
    assert result == {"published": 0, "failed": 1, "expired": 0}
    assert outbox.list_pending()[0]["attempts"] == 2


def test_dispatcher_expires_old_events(tmp_path):
    outbox = EventOutbox(tmp_path / "events.json")
    outbox.publish({"event_id": "old", "kind": "new", "created_at": time.time() - 100})
    dispatcher = EventDispatcher(outbox, publish=lambda _event: True, max_age_seconds=10)

    result = asyncio.run(dispatcher.dispatch_once())
    assert result["expired"] == 1
    assert outbox.list_pending() == []
