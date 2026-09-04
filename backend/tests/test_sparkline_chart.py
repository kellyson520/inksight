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
    # 验证在 flex_row 行中，价格（黑色 0）与涨跌徽标（红色 3）并排居中且保持安全水平间隙，无水平碰撞
    row_checked = False
    for y in range(90, 140):
        red_cols = np.where(arr[y, :] == 3)[0]
        black_cols = np.where(arr[y, :] == 0)[0]
        if len(red_cols) > 0 and len(black_cols) > 0:
            black_right = black_cols[black_cols < red_cols.min()].max() if any(black_cols < red_cols.min()) else 0
            red_left = red_cols.min()
            assert red_left - black_right >= 8, f"Expected gap >= 8, got {red_left - black_right}"
            row_checked = True
    assert row_checked, "Flex row with price and change badge should exist"

