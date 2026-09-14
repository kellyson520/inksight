import pytest
from unittest.mock import patch
from core.patterns.utils import format_compact_number
from core.providers.oil_price_provider import (
    generate_oil_price,
    format_oil_data,
    PROVINCE_OIL_PRICES,
)
from core.pipeline import generate_and_render

def test_format_compact_number_formats_correctly():
    assert format_compact_number(1250000) == "125万"
    assert format_compact_number(1254000) == "125.4万"
    assert format_compact_number(350000000) == "3.5亿"
    assert format_compact_number(950) == "950"
    assert format_compact_number("1285000") == "128.5万"
    assert format_compact_number("94.8%") == "94.8%"

def test_format_oil_data_calculates_prediction_and_prices():
    data = format_oil_data("山东", countdown_days=3, expected_change_per_ton=-140)
    assert data["province"] == "山东"
    assert data["countdown_days"] == 3
    assert data["is_drop"] is True
    assert "下调" in data["trend_text"]
    assert float(data["gas_92"]) > 6.0
    assert float(data["gas_95"]) > float(data["gas_92"])
    assert float(data["gas_98"]) > float(data["gas_95"])
    assert float(data["diesel_0"]) > 5.0

@pytest.mark.asyncio
async def test_oil_price_provider_fallback_and_overrides():
    # 测试自定义省份配置覆盖
    cfg = {
        "mode_overrides": {
            "OIL_PRICE": {
                "province": "北京"
            }
        }
    }
    data = await generate_oil_price(
        mode_def={"mode_id": "OIL_PRICE"},
        content_cfg={"type": "computed", "provider": "oil_price"},
        fallback={"province": "山东", "trend_text": "平稳"},
        config=cfg,
    )
    assert data["province"] == "北京"
    assert "gas_92" in data
    assert "gas_95" in data

@pytest.mark.asyncio
async def test_oil_price_renders_crisp_eink_board():
    img, content = await generate_and_render(
        "OIL_PRICE",
        {"province": "山东"},
        {"date_str": "9月14日 周一", "time_str": "12:00:00"},
        {"weather_str": "晴 22℃"},
        100,
        400,
        300,
    )
    assert img is not None
    assert img.size == (400, 300)
    assert content["province"] == "山东"
    # 验证生成了清晰黑色像素
    pixels = list(img.getdata())
    assert pixels.count(0) > 2500
