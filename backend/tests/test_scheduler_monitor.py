from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.asyncio
async def test_scheduler_registers_monitor_poll_job(monkeypatch):
    from core import scheduler as module

    calls = []
    fake_scheduler = SimpleNamespace(
        running=False,
        add_job=lambda *args, **kwargs: calls.append(kwargs),
        start=lambda: None,
        get_jobs=lambda: [],
    )
    monkeypatch.setattr(module, "scheduler", fake_scheduler)

    with patch("core.static_store.is_poetry_initialized", new=AsyncMock(return_value=True)):
        await module.start_scheduler()

    assert any(call.get("id") == "monitor_poll" for call in calls)
    assert any(call.get("id") == "hotlist_diff_poll" for call in calls)
