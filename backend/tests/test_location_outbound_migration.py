from unittest.mock import patch

import pytest

from core.location_service import _fetch_geocoding


@pytest.mark.asyncio
async def test_geocoding_uses_shared_outbound_http():
    response = type("Response", (), {"json": lambda self: {"results": [{"name": "Hangzhou"}]}})()
    with patch("core.location_service.outbound_http.get_json", return_value=response) as get_json:
        result = await _fetch_geocoding("Hangzhou", count=2, language="en")

    assert result == {"results": [{"name": "Hangzhou"}]}
    get_json.assert_called_once()
    assert "name=Hangzhou" in get_json.call_args.args[0]
    assert "count=2" in get_json.call_args.args[0]
