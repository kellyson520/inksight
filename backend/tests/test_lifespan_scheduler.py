from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.asyncio
async def test_lifespan_starts_and_stops_scheduler():
    from api import shared

    with (
        patch.object(shared, "init_db", new=AsyncMock()),
        patch.object(shared, "init_stats_db", new=AsyncMock()),
        patch("core.cache.init_cache_db", new=AsyncMock()),
        patch("core.static_store.init_static_tables", new=AsyncMock()),
        patch("core.static_store.migrate_device_state_columns", new=AsyncMock()),
        patch("core.preload_store.init_preload_db", new=AsyncMock()),
        patch("core.preload_seeder.seed_preload_pool", new=AsyncMock()),
        patch("core.scheduler.start_scheduler", new=AsyncMock()) as start,
        patch("core.scheduler.stop_scheduler", new=AsyncMock()) as stop,
        patch("core.db.close_all", new=AsyncMock()),
    ):
        async with shared.lifespan(None):
            pass

    start.assert_awaited_once()
    stop.assert_awaited_once()
