"""
Tests for Gold Trend Mode (黄金趋势模式)
Verifies gold market data retrieval, timeseries resampling, provider dispatch, and e-ink image rendering.
"""
import pytest
from core.market_service import market_service
from core.providers.gold_provider import generate_gold
from core.pipeline import generate_and_render
from core.mode_registry import get_registry


@pytest.mark.asyncio
async def test_market_service_get_gold_data_domestic():
    """测试获取沪金主力 (AU0) 基础数据与分时折线。"""
    data = await market_service.get_gold_data("AU0")
    assert data is not None
    assert data["symbol"] == "AU0"
    assert "沪金" in data["name"]
    assert data["unit"] == "元/克"
    assert "¥" in data["currency_symbol"]
    assert "sparkline_data" in data
    assert len(data["sparkline_data"]) >= 10
    assert "ref_price" in data


@pytest.mark.asyncio
async def test_market_service_get_gold_data_international():
    """测试获取国际伦敦金 (XAU) 基础数据与分时折线。"""
    data = await market_service.get_gold_data("XAU")
    assert data is not None
    assert data["symbol"] == "XAU"
    assert "伦敦金" in data["name"]
    assert "盎司" in data["unit"] or "oz" in data["unit"]
    assert "$" in data["currency_symbol"]
    assert len(data["sparkline_data"]) >= 10
    assert "¥" in data["ref_price"]


@pytest.mark.asyncio
async def test_gold_provider_dispatch():
    """测试 Gold Provider 分发与配置继承。"""
    content = await generate_gold(
        mode_def={"mode_id": "GOLD"},
        content_cfg={"symbol": "AU0"},
        fallback={},
        config={"mode_overrides": {"GOLD": {"symbol": "XAU"}}},
    )
    assert content is not None
    assert content["symbol"] == "XAU"
    assert "price" in content
    assert "sparkline_data" in content


@pytest.mark.asyncio
async def test_gold_mode_registry_and_render():
    """测试黄金趋势模式注册与 400x300 E-Ink 图像渲染。"""
    reg = get_registry()
    mode = reg.get_json_mode("GOLD")
    assert mode is not None
    assert mode.definition["mode_id"] == "GOLD"

    img, content = await generate_and_render(
        "GOLD",
        config={"mode_overrides": {"GOLD": {"symbol": "AU0"}}},
        date_ctx={"time_str": "14:30", "date_str": "2026-09-05", "lunar_str": "七月廿五"},
        weather={"weather_str": "晴 25°C", "weather_code": 0},
        battery_pct=95.0,
        screen_w=400,
        screen_h=300,
        colors=4,
    )
    assert img is not None
    assert img.size == (400, 300)
    assert "sparkline_data" in content


@pytest.mark.asyncio
async def test_market_service_get_gold_data_au9999():
    """测试上海金交所 Au99.99 现货数据。"""
    data = await market_service.get_gold_data("AU9999")
    assert data is not None
    assert data["symbol"] == "AU9999"
    assert "上海金" in data["name"] or "Au99.99" in data["name"]
    assert data["unit"] == "元/克"
    assert len(data["sparkline_data"]) >= 10


@pytest.mark.asyncio
async def test_gold_mode_fallback_on_network_error():
    """测试网络异常时平滑降级到预设种子数据。"""
    from unittest.mock import patch, AsyncMock
    with patch("core.http_client.get_async_client") as mock_client:
        mock_instance = AsyncMock()
        mock_instance.get.side_effect = Exception("Simulated network down")
        mock_client.return_value = mock_instance

        # 强制清空缓存
        market_service._cache.pop("gold:AU0", None)
        data = await market_service.get_gold_data("AU0")
        assert data is not None
        assert data["symbol"] == "AU0"
        assert len(data["sparkline_data"]) >= 10


@pytest.mark.asyncio
async def test_gold_mode_renders_palette_colors():
    """测试 4 色模式下的调色板输出。"""
    img, content = await generate_and_render(
        "GOLD",
        config={"mode_overrides": {"GOLD": {"symbol": "XAU"}}},
        date_ctx={"time_str": "14:30", "date_str": "2026-09-05", "lunar_str": "七月廿五"},
        weather={"weather_str": "晴 25°C", "weather_code": 0},
        battery_pct=95.0,
        screen_w=400,
        screen_h=300,
        colors=4,
    )
    colors = dict((c[1], c[0]) for c in img.getcolors())
    # 0=黑, 1=白, 2=黄, 3=红
    assert colors.get(0, 0) > 0, "Black pixels must exist"
    assert colors.get(3, 0) > 0, "Red pixels must exist for badge/sparkline"
