from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.asyncio
async def test_start_scheduler_replaces_scheduler_bound_to_closed_loop(monkeypatch):
    from core import scheduler as module

    closed_loop = SimpleNamespace(is_closed=lambda: True)
    old = SimpleNamespace(running=False, _eventloop=closed_loop)
    monkeypatch.setattr(module, "scheduler", old)
    replacement = SimpleNamespace(running=False, add_job=lambda *a, **k: None, start=lambda: None, get_jobs=lambda: [])
    with patch("core.scheduler.AsyncIOScheduler", return_value=replacement), \
         patch("core.static_store.is_poetry_initialized", new=AsyncMock(return_value=True)):
        await module.start_scheduler()
    assert module.scheduler is replacement
