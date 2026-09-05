import asyncio

import pytest

from core.source_result import SourceResult
from core import rss_parser
from core.hotlist_service import HotlistService


def test_rss_returns_stale_data_when_refresh_fails(monkeypatch):
    rss_parser._RSS_CACHE.clear()
    payload = "<rss><channel><title>Feed</title><item><title>Old item</title></item></channel></rss>"

    class Response:
        text = payload

    now = [0.0]
    monkeypatch.setattr(rss_parser.time, "time", lambda: now[0])
    monkeypatch.setattr(rss_parser.outbound_http, "get_text", lambda *args, **kwargs: Response())
    first = asyncio.run(rss_parser.fetch_and_parse_rss("https://example.test/feed"))
    assert first["items"]

    monkeypatch.setattr(rss_parser.outbound_http, "get_text", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("down")))
    now[0] = 10_000.0
    result = asyncio.run(rss_parser.fetch_and_parse_rss("https://example.test/feed"))
    assert result["items"]
    assert result["source_status"] == "stale"


def test_rss_parse_failure_uses_stale_cache(monkeypatch):
    rss_parser._RSS_CACHE.clear()
    rss_parser._RSS_CACHE["https://example.test/feed"] = (0.0, {"items": [{"title": "old"}], "feed_title": "Feed"})
    monkeypatch.setattr(rss_parser.time, "time", lambda: 10_000.0)
    monkeypatch.setattr(rss_parser.outbound_http, "get_text", lambda *args, **kwargs: type("Response", (), {"text": "<rss><broken"})())

    result = asyncio.run(rss_parser.fetch_and_parse_rss("https://example.test/feed"))
    assert result["items"] == [{"title": "old"}]
    assert result["source_status"] == "stale"


@pytest.mark.asyncio
async def test_hotlist_preserves_fallback_status_on_cache_hit(monkeypatch):
    service = HotlistService(ttl=600)
    async def empty_fetch(*args, **kwargs):
        return []
    monkeypatch.setattr(service, "_fetch_platform_items", empty_fetch)

    first = await service.get_hotlist("zhihu", limit=1)
    second = await service.get_hotlist("zhihu", limit=1)

    assert first["source_status"] == "fallback"
    assert second["source_status"] == "fallback"
    assert len(second["items"]) == 1
    assert "item_2" not in second


@pytest.mark.asyncio
async def test_multi_hotlist_aggregates_source_status(monkeypatch):
    service = HotlistService(ttl=600)

    async def fetch(platform, limit):
        return [{"title": platform, "hot": "1"}] if platform == "zhihu" else []

    monkeypatch.setattr(service, "_fetch_platform_items", fetch)
    result = await service.get_multi_hotlist(["zhihu", "weibo"], limit=2)
    assert result["source_status"] in {"fresh", "stale", "fallback"}


def test_source_result_exposes_fresh_stale_and_fallback_status():
    fresh = SourceResult.fresh({"items": [1]}, source="rss")
    stale = fresh.as_stale(reason="timeout")
    fallback = SourceResult.fallback({"items": []}, source="rss", reason="unavailable")

    assert fresh.source_status == "fresh"
    assert stale.source_status == "stale"
    assert stale.data == fresh.data
    assert stale.error == "timeout"
    assert fallback.source_status == "fallback"
    assert fallback.data == {"items": []}
