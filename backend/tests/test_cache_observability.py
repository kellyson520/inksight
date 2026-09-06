from __future__ import annotations

from PIL import Image

from core.cache import ContentCache
from core.observability import obs
from core.db import close_all


async def test_cache_emits_miss_then_memory_hit(tmp_path):
    cache = ContentCache()
    config = {"refresh_interval": 60, "modes": ["DAILY"]}
    obs._events.clear()

    assert await cache.get("AA:BB", "DAILY", config) is None
    await cache.set("AA:BB", "DAILY", Image.new("1", (8, 8)), screen_w=8, screen_h=8, config=config)
    assert await cache.get("AA:BB", "DAILY", config, screen_w=8, screen_h=8) is not None

    results = [e.get("result") for e in obs.snapshot()["events"] if e["event"] == "cache.result"]
    assert "miss" in results
    assert "memory" in results
    await close_all()
