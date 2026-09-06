from unittest.mock import patch

import pytest

from core.location_service import _fetch_nominatim


@pytest.mark.asyncio
async def test_nominatim_uses_shared_outbound_http():
    response = type("Response", (), {"json": lambda self: [{"display_name": "杭州"}]})()
    with patch("core.location_service.outbound_http.get_json", return_value=response) as get_json:
        result = await _fetch_nominatim("杭州", count=3, country_codes="cn", locale="zh")

    assert result == [{"display_name": "杭州"}]
    get_json.assert_called_once()
    url = get_json.call_args.args[0]
    assert "q=%E6%9D%AD%E5%B7%9E" in url
    assert "limit=3" in url
    assert "countrycodes=cn" in url
    assert get_json.call_args.kwargs["headers"]["User-Agent"]
