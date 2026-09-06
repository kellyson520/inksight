from unittest.mock import Mock, patch

import pytest

from core.monitor_service import MonitorService
from core.outbound_http import outbound_http


@pytest.mark.asyncio
async def test_monitor_check_uses_outbound_http_adapter():
    service = MonitorService()
    target = {
        "id": "m1",
        "name": "example",
        "url": "https://example.test/page",
        "enabled": True,
        "last_hash": "",
        "last_summary": "",
    }
    response = type("Response", (), {"text": "<title>ok</title><main>stable</main>"})()
    adapter = Mock()
    adapter.get_text.return_value = response
    with patch("core.monitor_service.outbound_http", adapter):
        assert await service.check_target(target) is None
    adapter.get_text.assert_called_once()


@pytest.mark.asyncio
async def test_monitor_check_rejects_private_url_before_fetch():
    service = MonitorService()
    target = {
        "id": "m2",
        "name": "private",
        "url": "http://127.0.0.1:8080/admin",
        "enabled": True,
    }
    with patch("core.monitor_service.outbound_http", outbound_http) as adapter:
        assert await service.check_target(target) is None
    assert target["last_status"] == "error"
