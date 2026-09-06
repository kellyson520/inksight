import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from core.outbound_http import HttpResponse


@pytest.mark.asyncio
async def test_scheduler_wikipedia_uses_shared_outbound(monkeypatch):
    from core import scheduler as module

    payload = {"selected": [{"year": 2000, "text": "A sufficiently long historical event", "pages": []}]}
    calls = []

    def fake_get_json(url, *, headers=None, policy=None):
        calls.append((url, headers, policy))
        return HttpResponse(200, {}, json.dumps(payload).encode(), url, 1, 1.0)

    monkeypatch.setattr(module, "outbound_http", SimpleNamespace(get_json=fake_get_json), raising=False)
    result = await module._fetch_wikipedia_thisday(9, 6)
    assert result and result[0]["year"] == 2000
    assert calls and "onthisday/all/09/06" in calls[0][0]
    assert calls[0][1]["Accept"] == "application/json"


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
    assert any(call.get("id") == "event_outbox_dispatch" for call in calls)
