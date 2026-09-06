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
@pytest.mark.asyncio
async def test_dispatchers_do_not_publish_same_event_while_lease_is_active(tmp_path):
    outbox = EventOutbox(tmp_path / "events.json")
    outbox.publish({"event_id": "e1", "kind": "new"})
    first_seen = []
    second_seen = []

    async def first_publish(event):
        first_seen.append(event["event_id"])
        return True

    async def second_publish(event):
        second_seen.append(event["event_id"])
        return True

    first = EventDispatcher(outbox, publish=first_publish, worker_id="worker-a", backoff=0)
    second = EventDispatcher(outbox, publish=second_publish, worker_id="worker-b", backoff=0)
    await first.dispatch_once()
    await second.dispatch_once()
    assert first_seen == ["e1"]
    assert second_seen == []


@pytest.mark.asyncio
async def test_dispatcher_keeps_failed_event_and_persists_attempts(tmp_path):
    path = tmp_path / "events.json"
    outbox = EventOutbox(path)
    outbox.publish({"event_id": "e1", "kind": "new"})

    async def publish(_event):
        return False

    result = await EventDispatcher(outbox, publish=publish, max_attempts=2, backoff=0).dispatch_once()
    assert result == {"published": 0, "failed": 1, "expired": 0}
    assert EventOutbox(path).list_pending()[0]["attempts"] == 2


@pytest.mark.asyncio
async def test_dispatcher_claims_events_for_worker_before_publishing(tmp_path):
    outbox = EventOutbox(tmp_path / "events.json")
    outbox.publish({"event_id": "e1", "kind": "new"})
    seen = []

    async def publish(event):
        seen.append(event["claimed_by"])
        return True

    dispatcher = EventDispatcher(outbox, publish=publish, worker_id="worker-a", backoff=0)
    await dispatcher.dispatch_once()
    assert seen == ["worker-a"]


@pytest.mark.asyncio
async def test_dispatcher_does_not_ack_truthy_non_boolean_result(tmp_path):
    outbox = EventOutbox(tmp_path / "events.json")
    outbox.publish({"event_id": "e1", "kind": "new"})

    result = await EventDispatcher(outbox, publish=lambda _event: "ok", max_attempts=1, backoff=0).dispatch_once()
    assert result["failed"] == 1
    assert len(outbox.list_pending()) == 1


def test_dispatcher_expires_old_events(tmp_path):
    outbox = EventOutbox(tmp_path / "events.json")
    outbox.publish({"event_id": "old", "kind": "new", "created_at": time.time() - 100})
    dispatcher = EventDispatcher(outbox, publish=lambda _event: True, max_age_seconds=10)

    result = asyncio.run(dispatcher.dispatch_once())
    assert result["expired"] == 1
    assert outbox.list_pending() == []
