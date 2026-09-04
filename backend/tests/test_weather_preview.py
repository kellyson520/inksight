import pytest
from fastapi.testclient import TestClient
from api.index import app
from core.patterns.utils import get_weather_icon, get_mode_icon
from core.weather_service import get_weather_forecast


def test_weather_icon_and_mode_icon_with_size():
    # 1. 验证 get_weather_icon 接收 size 参数正常缩放
    w_icon = get_weather_icon(0, size=(24, 24))
    assert w_icon is not None
    assert w_icon.size == (24, 24)

    # 2. 验证 get_mode_icon 接收 size 参数正常缩放
    m_icon = get_mode_icon("DAILY", size=(16, 16))
    assert m_icon is not None
    assert m_icon.size == (16, 16)


@pytest.mark.asyncio
async def test_weather_forecast_default_city_fallback():
    # 验证当 city=None 时，正确回退到 DEFAULT_CITY，不再发生 NameError
    res = await get_weather_forecast(city=None, days=1)
    assert res is not None
    assert res.get("city") == "杭州"
    assert "forecast" in res


def test_weather_preview_endpoint():
    with TestClient(app) as client:
        resp = client.get("/api/preview?persona=WEATHER&colors=3&w=400&h=300")
        assert resp.status_code == 200
        assert resp.headers.get("content-type") == "image/png"
        assert len(resp.content) > 100
