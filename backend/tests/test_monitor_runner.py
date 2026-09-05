from __future__ import annotations

import asyncio

import pytest

from core.monitor_runner import MonitorRunner


@pytest.mark.asyncio
async def test_monitor_runner_checks_due_targets_and_stops():
    checked: list[str] = []
    sleeps = 0

    class Service:
        def list_targets(self):
            return [
                {"id": "due", "enabled": True, "check_interval": 1, "last_checked": 0},
                {"id": "disabled", "enabled": False, "check_interval": 1, "last_checked": 0},
            ]

        async def check_target(self, target):
            checked.append(target["id"])

    async def sleep(_seconds):
        nonlocal sleeps
        sleeps += 1
        runner.stop()

    runner = MonitorRunner(Service(), now=lambda: 10, sleep=sleep, poll_interval=0)
    await runner.run_once()
    assert checked == ["due"]

    task = asyncio.create_task(runner.run_forever())
    await asyncio.wait_for(task, timeout=1)
    assert sleeps == 1


@pytest.mark.asyncio
async def test_monitor_runner_isolates_target_errors():
    checked: list[str] = []

    class Service:
        def list_targets(self):
            return [
                {"id": "bad", "enabled": True, "check_interval": 1, "last_checked": 0},
                {"id": "good", "enabled": True, "check_interval": 1, "last_checked": 0},
            ]

        async def check_target(self, target):
            if target["id"] == "bad":
                raise RuntimeError("boom")
            checked.append(target["id"])

    runner = MonitorRunner(Service(), now=lambda: 10, sleep=asyncio.sleep, poll_interval=0)
    await runner.run_once()
    assert checked == ["good"]
