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
