import pytest
from PIL import Image, ImageDraw
from core.mode_registry import get_registry
from core.json_renderer import render_json_mode
from core.hotlist_service import hotlist_service
from core.blocks.context import RenderContext
from core.blocks.hotlist import render_hotlist_board

@pytest.mark.asyncio
async def test_hotlist_service_extracts_8_items_and_metadata():
    """Verify get_hotlist returns 8 items with metadata across platforms."""
    for plat in ["weibo", "zhihu", "bilibili", "baidu", "douyin", "netease"]:
        res = await hotlist_service.get_hotlist(plat, limit=8)
        assert res is not None
        assert "items" in res
        assert len(res["items"]) >= 5
        first = res["items"][0]
        assert "rank" in first
        assert "title" in first
        assert "platform" in first
        assert "hot_value" in first

def test_hotlist_board_renders_8_items_dense_grid():
    """Verify dense_grid renders 8 items on screen."""
    img = Image.new("1", (400, 300), 1)
    draw = ImageDraw.Draw(img)
    items = [
        {"rank": i, "title": f"热点新闻标题 #{i} 科技生活前沿", "platform": "weibo", "platform_name": "微博", "hot_value": f"{100 - i * 10}万", "is_top": i <= 3}
        for i in range(1, 9)
    ]
    content = {"items": items, "style": "dense_grid"}
    ctx = RenderContext(
        img=img,
        draw=draw,
        content=content,
        screen_w=400,
        screen_h=300,
        colors=2,
        x_offset=0,
        y=40,
        available_width=400,
        footer_height=24,
    )
    render_hotlist_board(ctx, {"max_items": 8, "style": "dense_grid"})
    assert ctx.y > 40
    assert ctx.y <= 300 - 24

def test_hotlist_board_renders_8_items_classic():
    """Verify classic style renders 8 items on screen."""
    img = Image.new("1", (400, 300), 1)
    draw = ImageDraw.Draw(img)
    items = [
        {"rank": i, "title": f"知乎高赞问题回答讨论 #{i}", "platform": "zhihu", "platform_name": "知乎", "hot_value": f"{1000 - i * 80}", "is_top": i <= 3}
        for i in range(1, 9)
    ]
    content = {"items": items, "style": "classic"}
    ctx = RenderContext(
        img=img,
        draw=draw,
        content=content,
        screen_w=400,
        screen_h=300,
        colors=2,
        x_offset=0,
        y=40,
        available_width=400,
        footer_height=24,
    )
    render_hotlist_board(ctx, {"max_items": 8, "style": "classic"})
    assert ctx.y > 40
    assert ctx.y <= 300 - 24

def test_hotlist_board_renders_editorial_and_cover_card():
    """Verify editorial and cover_card styles render correctly."""
    img = Image.new("1", (400, 300), 1)
    draw = ImageDraw.Draw(img)
    test_cover = Image.new("RGB", (320, 180), (30, 80, 150))
    items = [
        {
            "rank": 1,
            "title": "B站头条热门推荐视频作品",
            "platform": "bilibili",
            "platform_name": "B站",
            "hot_value": "128万",
            "is_top": True,
            "cover_url": "https://example.com/cover.jpg",
            "image_data": test_cover,
        }
    ] + [
        {"rank": i, "title": f"次要热门条目 #{i}", "platform": "bilibili", "platform_name": "B站", "hot_value": "50万", "is_top": i <= 3}
        for i in range(2, 9)
    ]
    
    # Test editorial
    content_ed = {"items": items, "style": "editorial"}
    ctx_ed = RenderContext(
        img=img, draw=draw, content=content_ed, screen_w=400, screen_h=300, colors=2, x_offset=0, y=40, available_width=400, footer_height=24
    )
    render_hotlist_board(ctx_ed, {"style": "editorial"})
    assert ctx_ed.y > 40

    # Test cover_card
    content_card = {"items": items, "style": "cover_card"}
    ctx_card = RenderContext(
        img=img, draw=draw, content=content_card, screen_w=400, screen_h=300, colors=2, x_offset=0, y=40, available_width=400, footer_height=24
    )
    render_hotlist_board(ctx_card, {"style": "cover_card"})
    assert ctx_card.y > 40

def test_standalone_hotlist_modes_in_registry():
    """Verify new standalone hotlist modes are registered in ModeRegistry."""
    reg = get_registry()
    for mode_id in ["WEIBO", "ZHIHU", "BILIBILI", "BAIDU", "DOUYIN", "NETEASE", "TECH_NEWS", "WECHAT_HOT", "GITHUB_TRENDING", "TIEBA"]:
        mode_def = reg.get_json_mode(mode_id)
        assert mode_def is not None, f"Mode {mode_id} must be registered"
        assert mode_def.definition.get("content", {}).get("provider") == "hotlist"

@pytest.mark.asyncio
async def test_standalone_modes_immune_to_douban_interference():
    """Verify standalone modes are 100% immune to external dirty overrides containing Douban or other platforms."""
    from core.providers.hotlist_provider import generate_hotlist

    dirty_config = {
        "mode_overrides": {
            "WEIBO": {"platforms": ["douban", "netease"]},
            "BILIBILI": {"platforms": ["douban"]},
            "NETEASE": {"platforms": ["douban", "wechat"]},
            "TECH_NEWS": {"platforms": ["douban"]},
            "HOTLIST": {"platforms": ["douban"]},
        }
    }

    # 1. Test WEIBO with dirty Douban override
    res_weibo = await generate_hotlist(
        {"mode_id": "WEIBO"},
        {"provider": "hotlist", "platform": "weibo"},
        {},
        config=dirty_config,
    )
    assert res_weibo["platform"] == "weibo"
    assert res_weibo["platform_title"] == "微博实时热搜"
    for item in res_weibo["items"]:
        assert item["platform"] == "weibo"
        assert "豆瓣" not in item.get("platform_name", "")

    # 2. Test BILIBILI with dirty Douban override
    res_bili = await generate_hotlist(
        {"mode_id": "BILIBILI"},
        {"provider": "hotlist", "platform": "bilibili"},
        {},
        config=dirty_config,
    )
    assert res_bili["platform"] == "bilibili"
    assert res_bili["platform_title"] == "哔哩哔哩热门推荐"
    for item in res_bili["items"]:
        assert item["platform"] == "bilibili"
        assert "豆瓣" not in item.get("platform_name", "")

    # 3. Test NETEASE with dirty Douban override
    res_netease = await generate_hotlist(
        {"mode_id": "NETEASE"},
        {"provider": "hotlist", "platform": "netease"},
        {},
        config=dirty_config,
    )
    assert res_netease["platform"] == "netease"
    assert res_netease["platform_title"] == "网易云音乐热歌榜"
    for item in res_netease["items"]:
        assert item["platform"] == "netease"
        assert "豆瓣" not in item.get("platform_name", "")

    # 4. Test TECH_NEWS with dirty Douban override
    res_tech = await generate_hotlist(
        {"mode_id": "TECH_NEWS"},
        {"provider": "hotlist", "platforms": ["36kr", "ithome", "sspai", "github"]},
        {},
        config=dirty_config,
    )
    for item in res_tech["items"]:
        assert item["platform"] in ["36kr", "ithome", "sspai", "github"]
        assert item["platform"] != "douban"
