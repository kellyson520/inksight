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
        return Image.new("1", (8, 8), 0), {"text": "generated"}

    results = await asyncio.gather(*[
        cache.get_or_generate("AA:BB", "DAILY", {}, generate, ttl_minutes=10, screen_w=8, screen_h=8)
        for _ in range(5)
    ])
    assert calls == 1
    assert all(result[0] is not None for result in results)
    assert len({id(result[0]) for result in results}) == 5
    assert all(result[1] == {"text": "generated"} for result in results)
    await close_all()


@pytest.mark.asyncio
async def test_get_or_generate_cache_hit_preserves_tuple_contract():
    cache = ContentCache()
    config = {}
    await cache.set("AA:BE", "DAILY", Image.new("1", (8, 8)), screen_w=8, screen_h=8, config=config)
    async def unused_generator():
        raise AssertionError("cache hit should not generate")
    result = await cache.get_or_generate("AA:BE", "DAILY", config, unused_generator, screen_w=8, screen_h=8)
    assert isinstance(result, tuple)
    assert result[0].size == (8, 8)
    assert result[1] is None
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


@pytest.mark.asyncio
async def test_cancelled_waiter_does_not_cancel_shared_generation():
    cache = ContentCache()
    started = asyncio.Event()
    release = asyncio.Event()

    async def generate():
        started.set()
        await release.wait()
        return Image.new("1", (8, 8), 0)

    first = asyncio.create_task(cache.get_or_generate("AA:DD", "DAILY", {}, generate, screen_w=8, screen_h=8))
    await started.wait()
    second = asyncio.create_task(cache.get_or_generate("AA:DD", "DAILY", {}, generate, screen_w=8, screen_h=8))
    first.cancel()
    with pytest.raises(asyncio.CancelledError):
        await first
    release.set()
    result = await second
    assert result.size == (8, 8)
    await close_all()
