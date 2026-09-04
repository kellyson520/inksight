import pytest
from core.preload_store import get_preload_count, get_next_preload_item, add_preload_item
from core.preload_seeder import seed_preload_pool
from core.pipeline import generate_and_render
from core.db import close_all


@pytest.fixture(autouse=True)
async def cleanup_db_connections():
    yield
    await close_all()


@pytest.mark.asyncio
async def test_preload_seeding_coverage():
    """验证所有核心 LLM 模式都已预置充足的离线池条目。"""
    await seed_preload_pool(days_ahead=7)
    modes_expected = [
        "WORD_OF_THE_DAY", "RIDDLE", "LETTER", "DAILY",
        "MY_QUOTE", "STOIC", "ROAST", "ZEN",
        "STORY", "POETRY", "QUESTION", "BIAS", "CHALLENGE"
    ]
    for mode in modes_expected:
        cnt = await get_preload_count(mode)
        assert cnt >= 5, f"Mode {mode} should have at least 5 preloaded items, got {cnt}"


@pytest.mark.asyncio
async def test_word_of_the_day_no_stuck_serendipity():
    """验证每日一词连续获取时自动轮换，绝不再卡死重复 Serendipity。"""
    device_mac = "TEST_SERENDIPITY_REGRESSION"
    words = []
    for _ in range(8):
        item = await get_next_preload_item("WORD_OF_THE_DAY", mac=device_mac)
        assert item is not None
        words.append(item["word"])

    # 验证 8 次获取全部互不相同
    assert len(set(words)) == 8
    # 验证第一条之后绝不是连续的 Serendipity
    assert words.count("Serendipity") <= 1


@pytest.mark.asyncio
async def test_riddle_and_letter_render_without_key():
    """验证猜谜与慢信在无大模型 API Key 情况下依然能优雅降级并成功渲染。"""
    date_ctx = {"time_str": "12:00", "date_str": "2026-09-04", "lunar_str": "七月廿四"}
    weather = {"weather_str": "晴 26°C", "weather_code": 0}

    for mode in ["RIDDLE", "LETTER"]:
        img, content = await generate_and_render(
            mode, {}, date_ctx, weather, 80, 400, 300, mac="TEST_NO_KEY", colors=2
        )
        assert img is not None
        assert img.size == (400, 300)
        assert content is not None
        # 必须含有该模式的核心字段
        if mode == "RIDDLE":
            assert "question" in content and "answer" in content
        elif mode == "LETTER":
            assert "greeting" in content and "body" in content


@pytest.mark.asyncio
async def test_all_llm_modes_render_cleanly():
    """验证所有 LLM 模式（ROAST, ZEN, STORY, POETRY, QUESTION, BIAS, CHALLENGE）均能通过预存池顺畅渲染。"""
    date_ctx = {"time_str": "12:00", "date_str": "2026-09-04", "lunar_str": "七月廿四"}
    weather = {"weather_str": "阴 20°C", "weather_code": 2}

    modes = ["ROAST", "ZEN", "STORY", "POETRY", "QUESTION", "BIAS", "CHALLENGE"]
    for mode in modes:
        img, content = await generate_and_render(
            mode, {}, date_ctx, weather, 90, 400, 300, mac=f"TEST_RENDER_{mode}", colors=4
        )
        assert img is not None
        assert img.size == (400, 300)
        assert content is not None


@pytest.mark.asyncio
async def test_dynamic_pool_addition_and_hash_dedup():
    """验证向预存池动态补充条目时的幂等性与去重机制。"""
    import uuid
    from core.db import get_main_db
    unique_word = f"Echo_{uuid.uuid4().hex[:6]}"
    test_item = {"word": unique_word, "phonetic": "/test/", "definition": "测试回声"}
    ok1 = await add_preload_item("WORD_OF_THE_DAY", test_item)
    assert ok1 is True

    # 再次插入完全相同内容，应被内容 hash 拦截并返回 False (防止重复注入相同内容)
    ok2 = await add_preload_item("WORD_OF_THE_DAY", test_item)
    assert ok2 is False

    # 清理测试数据
    db = await get_main_db()
    await db.execute("DELETE FROM content_preload_pool WHERE content_json LIKE ?", (f"%{unique_word}%",))
    await db.commit()
