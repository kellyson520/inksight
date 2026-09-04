import pytest
from fastapi.testclient import TestClient
from api.index import app
from core.http_client import get_async_client, get_sync_client
from core.market_service import market_service
from core.hotlist_service import hotlist_service


def test_http_client_pool():
    client_sync = get_sync_client()
    assert client_sync is not None
    assert not client_sync.is_closed

    client_async = get_async_client()
    assert client_async is not None
    assert not client_async.is_closed


@pytest.mark.asyncio
async def test_market_service_crypto_and_stock():
    # 测试加密货币行情获取
    btc = await market_service.get_market_data("BTC")
    assert btc is not None
    assert "symbol" in btc
    assert "price" in btc
    assert len(btc.get("sparkline_data", [])) >= 10

    # 测试股票行情获取
    aapl = await market_service.get_market_data("AAPL")
    assert aapl is not None
    assert aapl["symbol"] == "AAPL"
    assert len(aapl.get("sparkline_data", [])) >= 10


@pytest.mark.asyncio
async def test_hotlist_service_aggregation():
    zhihu = await hotlist_service.get_hotlist("zhihu", limit=5)
    assert zhihu is not None
    assert zhihu["platform"] == "zhihu"
    assert len(zhihu.get("items", [])) >= 3
    assert "item_1" in zhihu


def test_api_endpoints_integration():
    client = TestClient(app)

    # 1. Market Quote API
    r1 = client.get("/api/market/quote?symbol=BTC")
    assert r1.status_code == 200
    res1 = r1.json()
    assert res1["success"] is True
    assert "price" in res1

    # 2. Market Timeseries API
    r2 = client.get("/api/market/timeseries?symbol=TSLA")
    assert r2.status_code == 200
    res2 = r2.json()
    assert res2["success"] is True
    assert res2["points_count"] >= 10

    # 3. Hotlist Platforms API
    r3 = client.get("/api/hotlist/platforms")
    assert r3.status_code == 200
    res3 = r3.json()
    assert res3["success"] is True
    assert len(res3["platforms"]) >= 4

    # 4. Hotlist Detail API
    r4 = client.get("/api/hotlist/bilibili?limit=4")
    assert r4.status_code == 200
    res4 = r4.json()
    assert res4["success"] is True
    assert len(res4["data"]["items"]) <= 4
