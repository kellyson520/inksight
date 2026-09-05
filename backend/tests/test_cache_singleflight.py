import asyncio

import pytest
from PIL import Image

from core.cache import ContentCache
from core.db import close_all


@pytest.mark.asyncio
async def test_get_or_generate_single_flight_runs_generator_once(monkeypatch):
    cache = ContentCache()
    await cache.clear()
    calls = 0

    async def generate():
        nonlocal calls
        calls += 1
        await asyncio.sleep(0.01)
        return Image.new("1", (8, 8), 0)

    results = await asyncio.gather(*[
        cache.get_or_generate("AA:BB", "DAILY", {}, generate, ttl_minutes=10, screen_w=8, screen_h=8)
        for _ in range(5)
    ])
    assert calls == 1
    assert all(result is not None for result in results)
    await close_all()


@pytest.mark.asyncio
async def test_get_or_generate_shares_failure_then_allows_retry():
    cache = ContentCache()
    await cache.clear()
    calls = 0

    async def fail_once():
        nonlocal calls
        calls += 1
        await asyncio.sleep(0)
        raise RuntimeError("boom")

    results = await asyncio.gather(*[
        cache.get_or_generate("AA:CC", "DAILY", {}, fail_once, ttl_minutes=10, screen_w=8, screen_h=8)
        for _ in range(3)
    ], return_exceptions=True)
    assert calls == 1
    assert all(isinstance(result, RuntimeError) for result in results)

    with pytest.raises(RuntimeError):
        await cache.get_or_generate("AA:CC", "DAILY", {}, fail_once, ttl_minutes=10, screen_w=8, screen_h=8)
    assert calls == 2
    await close_all()
