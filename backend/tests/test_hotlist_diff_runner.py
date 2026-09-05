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
