import pytest
from core.providers import dispatch_provider
from core.pipeline import generate_and_render
from core.context import get_date_context


@pytest.mark.asyncio
async def test_crypto_sparkline_generation():
    mode_def = {"mode_id": "CRYPTO"}
    content_cfg = {"provider": "crypto", "symbol": "BTC"}
    fallback = {}
    
    res = await dispatch_provider("crypto", mode_def, content_cfg, fallback)
    assert res is not None
    assert "sparkline_data" in res
    assert isinstance(res["sparkline_data"], list)
    assert len(res["sparkline_data"]) >= 10
    # 验证点为 float 或 int
    for p in res["sparkline_data"]:
        assert isinstance(p, (int, float))


@pytest.mark.asyncio
async def test_stock_sparkline_generation():
    mode_def = {"mode_id": "CRYPTO"}
    content_cfg = {"provider": "crypto", "symbol": "AAPL"}
    fallback = {}
    
    res = await dispatch_provider("crypto", mode_def, content_cfg, fallback)
    assert res is not None
    assert "AAPL" in res.get("name", "")
    assert "sparkline_data" in res
    assert len(res["sparkline_data"]) >= 10


@pytest.mark.asyncio
async def test_render_with_sparkline_block():
    date_ctx = await get_date_context()
    weather = {"weather_str": "晴 22°C", "weather_code": 0}
    
    # 2 色渲染
    img_bw, _ = await generate_and_render("CRYPTO", None, date_ctx, weather, 100.0, colors=2)
    assert img_bw.size == (400, 300)
    assert img_bw.mode == "1"

    # 3 色渲染
    img_bwr, _ = await generate_and_render("CRYPTO", None, date_ctx, weather, 100.0, colors=3)
    assert img_bwr.size == (400, 300)
    assert img_bwr.mode == "P"


@pytest.mark.asyncio
async def test_crypto_price_and_percentage_no_overlap():
    import numpy as np
    date_ctx = await get_date_context()
    weather = {"weather_str": "晴 22°C", "weather_code": 0}
    cfg = {"mode_overrides": {"CRYPTO": {"symbol": "AAPL"}}}
    img, _ = await generate_and_render("CRYPTO", cfg, date_ctx, weather, 100.0, colors=3)
    arr = np.array(img)
    # 验证在 Y=100 到 Y=200 之间，黑色价格与红色涨跌幅行不发生像素行重叠
    price_black_rows = []
    change_red_rows = []
    for y in range(100, 200):
        row = set(arr[y, 100:300])
        if 0 in row:
            price_black_rows.append(y)
        if 3 in row:
            change_red_rows.append(y)
    
    assert price_black_rows, "Price text rows should exist"
    assert change_red_rows, "Change percentage text rows should exist"
    max_price_y = max(price_black_rows)
    min_change_y = min(change_red_rows)
    # 确保两者之间至少有 5 像素的正间距，绝对不重叠
    assert min_change_y - max_price_y >= 5, f"Expected gap >= 5, got {min_change_y - max_price_y}"

