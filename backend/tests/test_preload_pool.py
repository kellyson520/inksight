from datetime import date, timedelta
import pytest
from core.preload_store import (
    init_preload_db,
    add_preload_item,
    get_next_preload_item,
    get_preload_count,
)
from core.preload_seeder import seed_preload_pool
from core.pipeline import generate_content_only
from core.context import get_date_context


@pytest.mark.asyncio
async def test_preload_store_crud():
    await init_preload_db()
    from core.db import get_main_db
    db = await get_main_db()
    await db.execute("DELETE FROM content_preload_pool WHERE mode_id = 'TEST_MODE_UNIQUE'")
    await db.commit()

    # 写入测试数据
    added = await add_preload_item("TEST_MODE_UNIQUE", {"title": "Test Unique 1"}, target_date="2026-09-04")
    assert added is True
    # 重复写入防重
    added_dup = await add_preload_item("TEST_MODE_UNIQUE", {"title": "Test Unique 1"}, target_date="2026-09-04")
    assert added_dup is False

    # 同一内容可以用于不同日期；日期是预存池的数据维度
    added_other_date = await add_preload_item("TEST_MODE_UNIQUE", {"title": "Test Unique 1"}, target_date="2026-09-05")
    assert added_other_date is True

    # 读取
    item = await get_next_preload_item("TEST_MODE_UNIQUE", mac="DEVICE_A", target_date="2026-09-04")
    assert item is not None
    assert item["title"] == "Test Unique 1"
    assert item["_from_preload"] is True


@pytest.mark.asyncio
async def test_rolling_multi_day_thisday():
    await init_preload_db()
    await seed_preload_pool(days_ahead=7)

    today = date.today()
    mac = "DEVICE_ROLLING_TEST"

    # 模拟未来7天，每天请求 THISDAY
    seen_events = []
    for day_offset in range(7):
        target_day = today + timedelta(days=day_offset)
        target_day_str = target_day.isoformat()

        # 获取当天内容
        content = await get_next_preload_item("THISDAY", mac=mac, target_date=target_day_str)
        assert content is not None
        assert "event_title" in content
        seen_events.append((target_day_str, content["event_title"]))

    # 验证每天都有有效事件
    assert len(seen_events) == 7
    print("7-day rolling events:", seen_events)


@pytest.mark.asyncio
async def test_anti_llm_fluctuation_zero_wait():
    """验证即使在完全无 LLM API Key 的情况下，各核心模式仍能从预存池毫秒级稳定输出"""
    await init_preload_db()
    await seed_preload_pool(days_ahead=7)

    date_ctx = await get_date_context()
    weather = {"weather_str": "晴 22°C", "weather_code": 0}
    mac = "ANTI_FLUX_DEVICE"

    for mode in ["THISDAY", "DAILY", "WORD_OF_THE_DAY", "MY_QUOTE"]:
        res = await generate_content_only(mode, None, date_ctx, weather, mac=mac)
        assert res is not None
        assert res.get("_from_preload") is True
