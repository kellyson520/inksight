"""
微信读书推荐模式 (WECHAT_READ Mode) 单元测试
覆盖 Service、Provider、Mode Registry 与 400x300 墨水屏图片渲染。
"""
from __future__ import annotations

import pytest
from core.wechat_read_service import wechat_read_service
from core.providers.wechat_read_provider import generate_wechat_read
from core.providers import dispatch_provider, list_registered_providers
from core.pipeline import generate_and_render
from core.mode_registry import get_registry


def test_wechat_read_service_books():
    """测试书籍检索与分类过滤。"""
    all_books = wechat_read_service.get_books_by_category("ALL")
    assert len(all_books) >= 10

    lit_books = wechat_read_service.get_books_by_category("LITERATURE")
    assert len(lit_books) >= 2
    for b in lit_books:
        assert b["category"] == "LITERATURE"

    biz_books = wechat_read_service.get_books_by_category("BUSINESS")
    assert len(biz_books) >= 2


def test_wechat_read_service_recommendation():
    """测试单书推荐与格式化输出。"""
    book = wechat_read_service.get_recommended_book(category="HISTORY", seed="device_mac_123")
    assert book is not None
    assert "title" in book
    assert "《" in book["title_bracketed"]
    assert "author" in book
    assert "recommend_reason" in book
    assert "cover_url" in book
    assert "reading_count" in book


@pytest.mark.asyncio
async def test_wechat_read_provider_dispatch():
    """测试 Provider 调度及配置覆盖。"""
    assert "wechat_read" in list_registered_providers()

    mode_def = {"mode_id": "WECHAT_READ"}
    content_cfg = {"provider": "wechat_read", "category": "ALL"}
    fallback = {"title": "明朝那些事儿", "recommend_reason": "默认推荐理由"}

    # 1. 默认调用
    res = await dispatch_provider("wechat_read", mode_def, content_cfg, fallback)
    assert res is not None
    assert "title" in res
    assert "cover_url" in res
    assert "recommend_reason" in res

    # 2. 带配置覆盖（指定文学分类）
    res_override = await dispatch_provider(
        "wechat_read",
        mode_def,
        content_cfg,
        fallback,
        config={"mode_overrides": {"WECHAT_READ": {"category": "LITERATURE"}}},
    )
    assert res_override is not None
    assert res_override["category"] == "LITERATURE"


@pytest.mark.asyncio
async def test_wechat_read_mode_render_400x300():
    """测试 400x300 双栏布局渲染（左侧书名与推荐理由，右侧图书封面）。"""
    img, content = await generate_and_render(
        "WECHAT_READ",
        config={"mode_overrides": {"WECHAT_READ": {"category": "HISTORY"}}},
        date_ctx={"time_str": "15:00", "date_str": "2026-09-05", "lunar_str": "七月廿五"},
        weather={"weather_str": "晴 26°C", "weather_code": 0},
        battery_pct=88.0,
        screen_w=400,
        screen_h=300,
        colors=4,
    )
    assert img is not None
    assert img.size == (400, 300)
    assert "title" in content
    assert "recommend_reason" in content
    assert "cover_url" in content

    # 检查调色板像素
    colors = dict((c[1], c[0]) for c in img.getcolors())
    assert colors.get(0, 0) > 0, "Black pixels must exist"


@pytest.mark.asyncio
async def test_wechat_read_mode_registered():
    """测试 WECHAT_READ 模式成功注册至 ModeRegistry。"""
    registry = get_registry()
    mode = registry.get_json_mode("WECHAT_READ")
    assert mode is not None
    assert mode.info.mode_id == "WECHAT_READ"
    assert mode.info.display_name == "微信读书推荐"


@pytest.mark.asyncio
async def test_wechat_read_all_covers_render_without_placeholders():
    """回归测试：验证全部精选书籍封面图片均能正常下载并渲染，不出现 404 或占位符。"""
    from core.wechat_read_service import WECHAT_READ_BOOKS
    for book in WECHAT_READ_BOOKS:
        img, content = await generate_and_render(
            "WECHAT_READ",
            config={"mode_overrides": {"WECHAT_READ": {"book_id": book["id"]}}},
            date_ctx={"time_str": "15:00", "date_str": "2026-09-05"},
            weather={"weather_str": "晴", "weather_code": 0},
            battery_pct=90.0,
            screen_w=400,
            screen_h=300,
            colors=2,
        )
        assert img is not None
        assert content["id"] == book["id"]
        # 裁剪右侧封面区域 (x: 240..370, y: 30..190)
        crop = img.crop((240, 30, 360, 190))
        extrema = crop.getextrema()
        assert extrema == (0, 255), f"Book {book['title']} cover must have contrast"
