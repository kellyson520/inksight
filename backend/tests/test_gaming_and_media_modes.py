"""
Unit tests for the 13 gaming and media modes, and Steam profile preferences:
- XIAOHEIHE_DISCOUNT (小黑盒游戏折扣)
- EPIC_FREE (Epic喜加一)
- STEAM_ACHIEVEMENTS (Steam我的成就)
- GCORES_PODCAST (机核播客)
- MIYOUSHE_NEWS (米游社公告)
- STEAM_RECENT (Steam最近在玩)
- STEAM_RANDOM (Steam今天玩什么)
- STEAM_FRIENDS (Steam好友状态)
- GCORES_NEWS (机核资讯)
- GCORES_ARTICLES (机核文章)
- GAMERSKY_NEWS (游民星空单机资讯)
- CHUAPP_ARTICLES (触乐最新文章)
- YYSTV_ARTICLES (游研社最新文章)
"""
import pytest
from core.mode_registry import ModeRegistry
from core.pipeline import generate_and_render
from core.config_store import save_user_preferences, get_user_preferences


ALL_GAMING_MODES = [
    "XIAOHEIHE_DISCOUNT",
    "EPIC_FREE",
    "STEAM_ACHIEVEMENTS",
    "GCORES_PODCAST",
    "MIYOUSHE_NEWS",
    "STEAM_RECENT",
    "STEAM_RANDOM",
    "STEAM_FRIENDS",
    "GCORES_NEWS",
    "GCORES_ARTICLES",
    "GAMERSKY_NEWS",
    "CHUAPP_ARTICLES",
    "YYSTV_ARTICLES",
]


def test_all_13_gaming_modes_registered():
    """验证所有 13 个游戏与媒体模式均正确注册到 ModeRegistry 中。"""
    from core.mode_registry import get_registry
    registry = get_registry()
    modes = registry.list_modes()
    registered_ids = {m.mode_id for m in modes}

    for mode_id in ALL_GAMING_MODES:
        assert mode_id in registered_ids, f"Mode {mode_id} is missing from ModeRegistry!"


@pytest.mark.asyncio
async def test_steam_profile_url_preference_saving():
    """验证用户在个人信息中保存 Steam 个人主页链接。"""
    user_id = 9999
    test_steam_url = "https://steamcommunity.com/profiles/76561198978201763/"

    # 保存
    saved = await save_user_preferences(user_id, {
        "steam_profile_url": test_steam_url,
    })
    assert saved["steam_profile_url"] == test_steam_url

    # 读取
    retrieved = await get_user_preferences(user_id)
    assert retrieved["steam_profile_url"] == test_steam_url


@pytest.mark.asyncio
@pytest.mark.parametrize("mode_id", ALL_GAMING_MODES)
async def test_gaming_mode_pipeline_rendering(mode_id: str):
    """验证每个游戏与媒体模式都能在渲染管线中成功生成合法 400x300 图像。"""
    device_config = {
        "mac": "AA:BB:CC:DD:EE:FF",
        "city": "上海",
        "mode_overrides": {
            "STEAM_ACHIEVEMENTS": {"steam_url": "https://steamcommunity.com/profiles/76561198978201763/"},
            "STEAM_RECENT": {"steam_url": "https://steamcommunity.com/profiles/76561198978201763/"},
            "STEAM_RANDOM": {"steam_url": "https://steamcommunity.com/profiles/76561198978201763/"},
            "STEAM_FRIENDS": {"steam_url": "https://steamcommunity.com/profiles/76561198978201763/"},
        }
    }

    img, content = await generate_and_render(
        persona=mode_id,
        config=device_config,
        date_ctx={"time_str": "16:30", "date_str": "09/24", "weekday": 2, "day": 24},
        weather={"weather_str": "晴", "weather_code": 0},
        battery_pct=95.0,
        screen_w=400,
        screen_h=300,
        colors=2,
    )
    assert img is not None
    assert img.size == (400, 300)
    assert content is not None


@pytest.mark.asyncio
@pytest.mark.parametrize("mode_id", ALL_GAMING_MODES)
async def test_gaming_mode_pipeline_rendering_en_and_small_screen(mode_id: str):
    """验证游戏媒体模式在英文环境和 296x128 小屏墨水屏下的排版与渲染。"""
    device_config = {
        "mac": "AA:BB:CC:DD:EE:FF",
        "language": "en",
        "mode_language": "en",
        "mode_overrides": {
            "STEAM_ACHIEVEMENTS": {"steam_url": "https://steamcommunity.com/profiles/76561198978201763/"},
            "STEAM_RECENT": {"steam_url": "https://steamcommunity.com/profiles/76561198978201763/"},
            "STEAM_RANDOM": {"steam_url": "https://steamcommunity.com/profiles/76561198978201763/"},
            "STEAM_FRIENDS": {"steam_url": "https://steamcommunity.com/profiles/76561198978201763/"},
        }
    }

    img, content = await generate_and_render(
        persona=mode_id,
        config=device_config,
        date_ctx={"time_str": "16:30", "date_str": "Sep 24", "weekday": 2, "day": 24},
        weather={"weather_str": "Clear", "weather_code": 0},
        battery_pct=95.0,
        screen_w=296,
        screen_h=128,
        colors=2,
    )
    assert img is not None
    assert img.size == (296, 128)
    assert content is not None


@pytest.mark.asyncio
async def test_gaming_mode_pipeline_rendering_tri_color_and_quad_color():
    """验证游戏媒体模式在 3 色与 4 色彩色墨水屏下的调色板与像素格式兼容性。"""
    device_config = {
        "mac": "AA:BB:CC:DD:EE:FF",
        "city": "上海",
    }
    for c in (3, 4):
        img, content = await generate_and_render(
            persona="XIAOHEIHE_DISCOUNT",
            config=device_config,
            date_ctx={"time_str": "16:30", "date_str": "09/24", "weekday": 2, "day": 24},
            weather={"weather_str": "晴", "weather_code": 0},
            battery_pct=95.0,
            screen_w=400,
            screen_h=300,
            colors=c,
        )
        assert img is not None
        assert img.size == (400, 300)
        assert img.mode == "P"
        assert content is not None
