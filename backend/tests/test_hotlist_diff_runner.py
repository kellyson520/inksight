from __future__ import annotations

import pytest

from core.hotlist_diff_runner import HotlistDiffRunner


def test_diff_emits_new_and_rank_changed_events():
    runner = HotlistDiffRunner()
    first = runner.diff("zhihu", [{"title": "A"}, {"title": "B"}])
    second = runner.diff("zhihu", [{"title": "B"}, {"title": "C"}])

    assert first == []
    assert {event["kind"] for event in second} == {"new", "rank_changed", "removed"}
    assert next(event for event in second if event["kind"] == "new")["item_id"] == "c"


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
async def test_runner_marks_stale_events_non_realtime():
    events = []

    class Service:
        calls = 0
        async def get_hotlist(self, platform, limit=8):
            self.calls += 1
            return {"items": [{"title": "A"}] if self.calls == 1 else [{"title": "B"}], "source_status": "stale"}

    runner = HotlistDiffRunner(Service(), publish=events.append)
    await runner.run_once("zhihu")
    emitted = await runner.run_once("zhihu")
    assert emitted[0]["is_realtime"] is False
    assert events[0]["source_status"] == "stale"
