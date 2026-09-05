import asyncio
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
from types import SimpleNamespace

import pytest

from core import content


def test_news_and_feed_services_do_not_construct_http_clients_directly():
    paths = [
        "backend/core/rss_parser.py",
        "backend/core/content.py",
        "backend/core/context.py",
        "backend/core/weather_service.py",
        "backend/core/hotlist_service.py",
    ]
    for path in paths:
        source = (ROOT / path.removeprefix("backend/")).read_text()
        assert "httpx.AsyncClient" not in source
        assert "httpx.Client" not in source


@pytest.mark.asyncio
async def test_fetch_hn_top_stories_parses_outbound_json(monkeypatch):
    responses = {
        "https://hacker-news.firebaseio.com/v0/topstories.json": [101],
        "https://hacker-news.firebaseio.com/v0/item/101.json": {
            "title": "HN title",
            "score": 42,
            "url": "https://example.test/story",
        },
    }

    def fake_get_json(url, **kwargs):
        return SimpleNamespace(json=lambda: responses[url])

    monkeypatch.setattr(content.outbound_http, "get_json", fake_get_json)

    assert await content.fetch_hn_top_stories(limit=1) == [{
        "title": "HN title",
        "score": 42,
        "url": "https://example.test/story",
    }]


@pytest.mark.asyncio
async def test_fetch_hn_top_stories_isolates_failed_story(monkeypatch):
    def fake_get_json(url, **kwargs):
        if url.endswith("topstories.json"):
            return SimpleNamespace(json=lambda: [101, 202])
        if url.endswith("/101.json"):
            return SimpleNamespace(json=lambda: {
                "title": "kept",
                "score": 7,
                "url": "https://example.test/kept",
            })
        raise RuntimeError("story unavailable")

    monkeypatch.setattr(content.outbound_http, "get_json", fake_get_json)

    assert await content.fetch_hn_top_stories(limit=2) == [{
        "title": "kept",
        "score": 7,
        "url": "https://example.test/kept",
    }]
