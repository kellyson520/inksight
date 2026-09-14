import pytest
from unittest.mock import patch
from core.providers.currency_provider import (
    _parse_currency_rates,
    generate_currency,
    format_currency_item,
)
from core.pipeline import generate_and_render

def test_parse_currency_rates_from_api_response():
    # 测试对开放外汇 API 数据的解析与标准化
    mock_payload = {
        "result": "success",
        "base_code": "CNY",
        "rates": {
            "USD": 0.1381,
            "EUR": 0.1265,
            "JPY": 21.35,
            "HKD": 1.082,
            "GBP": 0.1082,
            "AUD": 0.2085,
        },
        "time_last_update_utc": "2026-09-14 12:00:00",
    }
    items = _parse_currency_rates(mock_payload, base="CNY")
    assert len(items) >= 5
    usd = next(item for item in items if item["currency"] == "USD")
    assert usd["name"] == "美元"
    assert usd["rate_cny"] > 7.0  # 1 USD ≈ 7.24 CNY
    assert "100 USD" in usd["calc_tip"]

def test_format_currency_item_produces_clean_badge():
    item = format_currency_item("USD", 7.2415, change_pct=0.15, base="CNY")
    assert item["currency"] == "USD"
    assert "7.2415" in str(item["rate"])
    assert "+0.15%" in item["change_str"] or "+0.2%" in item["change_str"]

@pytest.mark.asyncio
async def test_currency_provider_with_fallback_offline():
    # 模拟网络不可达时的稳健回退
    with patch("core.outbound_http.outbound_http.get_json", side_effect=RuntimeError("offline")):
        data = await generate_currency(
            mode_def={"mode_id": "CURRENCY"},
            content_cfg={"type": "computed", "provider": "currency"},
            fallback={"title": "全球主要汇率看板", "base_currency": "CNY", "items": []},
            config={},
        )
        assert data["title"]
        assert len(data["items"]) >= 4
        # 验证默认包含 USD、EUR、JPY、HKD 等关键货币
        cur_codes = [it["currency"] for it in data["items"]]
        assert "USD" in cur_codes
        assert "JPY" in cur_codes

@pytest.mark.asyncio
async def test_currency_mode_renders_clean_eink_card():
    img, content = await generate_and_render(
        "CURRENCY",
        {"base_currency": "CNY", "layout_style": "grid"},
        {"date_str": "9月14日 周一", "time_str": "12:00:00"},
        {"weather_str": "晴 22℃"},
        100,
        400,
        300,
    )
    assert img is not None
    assert img.size == (400, 300)
    assert len(content.get("items", [])) >= 4
    # 检查黑色像素充沛
    pixels = list(img.getdata())
    assert pixels.count(0) > 2000
