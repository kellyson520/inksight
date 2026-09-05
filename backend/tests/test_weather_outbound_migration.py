import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.weather_service import get_weather


@pytest.mark.parametrize("relative_path", ["core/context.py", "core/weather_service.py"])
def test_context_and_weather_do_not_construct_http_clients_directly(relative_path):
    source = (Path(__file__).parents[1] / relative_path).read_text()
    assert "httpx.AsyncClient" not in source
    assert "httpx.Client" not in source


@pytest.mark.asyncio
async def test_weather_json_failure_preserves_default_fallback():
    response = MagicMock()
    response.json.side_effect = json.JSONDecodeError("invalid", "{", 0)

    with (
        patch("core.weather_service.outbound_http.get_json", return_value=response) as get_json,
        patch("core.weather_service._qweather_current", new_callable=AsyncMock, return_value=None),
    ):
        result = await get_weather(lat=30.27, lon=120.15)

    assert result == {"temp": 0, "weather_code": -1, "weather_str": "--°C"}
    get_json.assert_called_once()


@pytest.mark.asyncio
async def test_weather_fetch_uses_outbound_http_in_worker_thread():
    response = MagicMock()
    response.json.return_value = {
        "current": {"temperature_2m": 15.3, "weather_code": 2}
    }

    with patch("core.weather_service.outbound_http.get_json", return_value=response) as get_json:
        result = await get_weather(lat=30.27, lon=120.15)

    assert result["temp"] == 15
    assert result["weather_code"] == 2
    get_json.assert_called_once()
