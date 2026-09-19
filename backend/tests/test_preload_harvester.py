"""
测试离线预存池自成长守护任务 (Autonomous Preload Harvester)
"""
import pytest
from unittest.mock import AsyncMock, patch
from core.preload_harvester import (
    PreloadHarvester,
    get_harvester_status,
    trigger_harvest_round,
    HARVEST_TARGET_MODES,
)
from core.preload_store import get_preload_count


@pytest.mark.asyncio
async def test_preload_harvester_status():
    status = await get_harvester_status()
    assert "target_modes" in status
    assert "modes_status" in status
    assert "total_cached" in status
    assert len(status["target_modes"]) >= 5


@pytest.mark.asyncio
async def test_trigger_harvest_round_generates_and_stores():
    harvester = PreloadHarvester(target_pool_size=5)

    mock_generated = {
        "quote": "千里之行，始于足下。",
        "author": "老子",
        "_llm_ok": True,
    }

    with (
        patch("core.preload_harvester.generate_json_mode_content", new_callable=AsyncMock, return_value=mock_generated),
        patch("core.preload_harvester.get_configured_llm_providers", return_value=[("deepseek", "deepseek-chat")]),
    ):
        result = await harvester.harvest_mode("DAILY", count=2)
        assert result["mode_id"] == "DAILY"
        assert result["generated_count"] >= 1

    # 验证确实存入了预存池
    count = await get_preload_count("DAILY")
    assert count >= 1
