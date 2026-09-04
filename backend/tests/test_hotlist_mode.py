import pytest
from core.hotlist_service import hotlist_service, PLATFORM_NAMES
from core.pipeline import generate_and_render


@pytest.mark.asyncio
async def test_hotlist_service_platforms_coverage():
    platforms = [
        "zhihu", "weibo", "bilibili", "douyin", "baidu",
        "36kr", "sspai", "ithome", "tieba", "github",
    ]
    for p in platforms:
        assert p in PLATFORM_NAMES
        data = await hotlist_service.get_hotlist(p, limit=5)
        assert data["platform"] == p
        assert len(data["items"]) > 0
        assert "title" in data["items"][0]
        assert "rank" in data["items"][0]


@pytest.mark.asyncio
async def test_hotlist_service_multi_interleaving():
    data = await hotlist_service.get_multi_hotlist(["zhihu", "weibo", "bilibili", "github"], limit=8)
    assert len(data["items"]) >= 4
    platforms_seen = {it["platform"] for it in data["items"]}
    assert len(platforms_seen) >= 2


@pytest.mark.asyncio
@pytest.mark.parametrize("style", ["dense_grid", "editorial", "classic"])
async def test_hotlist_render_all_styles(style):
    cfg = {
        "mac": "test-hotlist",
        "mode_overrides": {
            "HOTLIST": {
                "platforms": ["zhihu", "weibo", "36kr", "github"],
                "style": style,
            }
        },
    }
    date_ctx = {"time_str": "12:00", "date_str": "2026-09-04", "lunar_str": "七月廿四"}
    weather = {"weather_str": "晴 26°C", "weather_code": 0}

    img, content = await generate_and_render(
        "HOTLIST", cfg, date_ctx, weather, 85, 400, 300, mac="test-hotlist", colors=4
    )
    assert img.size == (400, 300)
    assert content is not None
    assert content.get("style") == style
    assert len(content.get("items", [])) > 0


@pytest.mark.asyncio
@pytest.mark.parametrize("res", [(296, 128), (400, 300), (800, 480)])
async def test_hotlist_multi_resolution(res):
    w, h = res
    cfg = {
        "mac": "test-res",
        "mode_overrides": {
            "HOTLIST": {
                "platforms": ["zhihu", "douyin", "ithome"],
                "style": "dense_grid",
            }
        },
    }
    date_ctx = {"time_str": "12:00", "date_str": "2026-09-04", "lunar_str": "七月廿四"}
    weather = {"weather_str": "多云 22°C", "weather_code": 1}

    img, _ = await generate_and_render(
        "HOTLIST", cfg, date_ctx, weather, 70, w, h, mac="test-res", colors=2
    )
    assert img.size == (w, h)
