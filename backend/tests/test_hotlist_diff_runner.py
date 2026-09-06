from __future__ import annotations

import json

import pytest

from core.hotlist_diff_runner import HotlistDiffRunner


def test_diff_emits_new_and_rank_changed_events():
    runner = HotlistDiffRunner()
    first = runner.diff("zhihu", [{"title": "A"}, {"title": "B"}])
    second = runner.diff("zhihu", [{"title": "B"}, {"title": "C"}])

    assert first == []
    assert {event["kind"] for event in second} == {"new", "rank_changed", "removed"}
    new_event = next(event for event in second if event["kind"] == "new")
    assert new_event["item_id"] == "c"
    rank_event = next(event for event in second if event["kind"] == "rank_changed")
    assert rank_event["old_rank"] == 2
    assert rank_event["rank"] == 1


@pytest.mark.asyncio
async def test_runner_publishes_diff_events():
    events = []

    class Service:
        async def get_hotlist(self, platform, limit=8):
            return {"items": [{"title": "A"}], "source_status": "fresh"}

    runner = HotlistDiffRunner(Service(), publish=events.append)
    emitted = await runner.run_once("zhihu")
    assert emitted == []
    assert events == []


@pytest.mark.asyncio
async def test_runner_marks_hotlist_events_for_broadcast_delivery():
    class Service:
        calls = 0
        async def get_hotlist(self, platform, limit=8):
            self.calls += 1
            title = "A" if self.calls == 1 else "B"
            return {"items": [{"title": title}], "source_status": "fresh"}

    runner = HotlistDiffRunner(Service())
    await runner.run_once("zhihu")
    events = await runner.run_once("zhihu")
    assert events
    assert all(event["target_mac"] == "*" for event in events)


@pytest.mark.asyncio
async def test_runner_ignores_fallback_as_snapshot_or_event():
    events = []

    class Service:
        calls = 0
        async def get_hotlist(self, platform, limit=8):
            self.calls += 1
            if self.calls == 1:
                return {"items": [{"title": "A"}], "source_status": "fresh"}
            return {"items": [{"title": "B"}], "source_status": "fallback"}

    runner = HotlistDiffRunner(Service(), publish=events.append)
    await runner.run_once("zhihu")
    assert await runner.run_once("zhihu") == []
    assert events == []


@pytest.mark.asyncio
async def test_runner_restores_snapshot_when_outbox_publish_fails(tmp_path):
    snapshot_path = tmp_path / "snapshots.json"
    calls = []

    class Service:
        count = 0
        async def get_hotlist(self, platform, limit=8):
            self.count += 1
            title = "A" if self.count == 1 else "B"
            return {"items": [{"title": title}], "source_status": "fresh"}

    def fail_publish(event):
        calls.append(event["event_id"])
        raise OSError("outbox unavailable")

    runner = HotlistDiffRunner(Service(), publish=fail_publish, snapshot_path=snapshot_path)
    await runner.run_once("zhihu")
    with pytest.raises(OSError):
        await runner.run_once("zhihu")

    assert json.loads(snapshot_path.read_text())["zhihu"] == {"a": 1}
    assert calls


@pytest.mark.asyncio
async def test_runner_restores_snapshot_when_snapshot_save_fails(tmp_path):
    snapshot_path = tmp_path / "snapshots.json"

    class Service:
        count = 0
        async def get_hotlist(self, platform, limit=8):
            self.count += 1
            title = "A" if self.count == 1 else "B"
            return {"items": [{"title": title}], "source_status": "fresh"}

    events = []
    runner = HotlistDiffRunner(Service(), publish=events.append, snapshot_path=snapshot_path)
    await runner.run_once("zhihu")
    runner._save_snapshots = lambda: (_ for _ in ()).throw(OSError("disk full"))
    with pytest.raises(OSError):
        await runner.run_once("zhihu")
    assert runner._snapshots["zhihu"] == {"a": 1}
    assert any(event["item_id"] == "b" for event in events)


@pytest.mark.asyncio
async def test_runner_restores_snapshot_from_disk(tmp_path):
    snapshot_path = tmp_path / "snapshots.json"

    class Service:
        async def get_hotlist(self, platform, limit=8):
            return {"items": [{"title": "A"}], "source_status": "fresh"}

    first = HotlistDiffRunner(Service(), snapshot_path=snapshot_path)
    await first.run_once("zhihu")
    second = HotlistDiffRunner(Service(), snapshot_path=snapshot_path)
    assert await second.run_once("zhihu") == []
    assert json.loads(snapshot_path.read_text())["zhihu"] == {"a": 1}


def test_outbox_assigns_creation_metadata(tmp_path):
    from core.event_outbox import EventOutbox
    outbox = EventOutbox(tmp_path / "events.json")
    outbox.publish({"event_id": "e1", "kind": "new"})
    item = outbox.list_pending()[0]
    assert item["created_at"] > 0
    assert item["attempts"] == 0
