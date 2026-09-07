import pytest
from unittest.mock import AsyncMock, patch
from core.source_health import source_health, SourceState
from core.hotlist_service import HotlistService
from core.rss_parser import fetch_rss_source


@pytest.mark.asyncio
async def test_hotlist_service_integrates_with_source_health():
    service = HotlistService(ttl=0)
    platform = "weibo"

    # Simulate 3 failures
    with patch.object(service, "_fetch_platform_items", side_effect=RuntimeError("connection error")):
        for _ in range(3):
            res = await service.get_hotlist(platform)
            assert res["source_status"] in ("stale", "fallback")

    # Verify source_health transitioned to COOLDOWN
    status = source_health.get_status(platform)
    assert status["state"] == SourceState.COOLDOWN
    assert status["consecutive_failures"] >= 3

    # On next call, _fetch_platform_items should NOT even be called due to cooldown
    with patch.object(service, "_fetch_platform_items", side_effect=AssertionError("Should not be called during cooldown!")):
        res_cooldown = await service.get_hotlist(platform)
        assert res_cooldown["source_status"] in ("stale", "fallback")


@pytest.mark.asyncio
async def test_rss_parser_integrates_with_source_health():
    url = "https://example.com/failing_feed.xml"

    with patch("core.rss_parser.outbound_http.get_text", side_effect=Exception("Host unreachable")):
        for _ in range(3):
            res = await fetch_rss_source(url)
            assert res.source_status in ("stale", "fallback")

    status = source_health.get_status(url)
    assert status["state"] == SourceState.COOLDOWN
    assert status["consecutive_failures"] >= 3

    # Next call should fast-fail without calling outbound_http
    with patch("core.rss_parser.outbound_http.get_text", side_effect=AssertionError("Should not call network in cooldown!")):
        res_fast = await fetch_rss_source(url)
        assert res_fast.source_status in ("stale", "fallback")
        assert res_fast.error == "circuit_breaker_cooldown"
