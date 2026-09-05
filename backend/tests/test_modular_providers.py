import pytest
from core.providers import dispatch_provider, list_registered_providers
from fastapi.testclient import TestClient
from api.index import app


def test_registered_providers():
    providers = list_registered_providers()
    assert "rss" in providers
    assert "crypto" in providers
    assert "gold" in providers
    assert "wechat_read" in providers


@pytest.mark.asyncio
async def test_crypto_provider():
    mode_def = {"mode_id": "CRYPTO"}
    content_cfg = {"provider": "crypto", "symbol": "BTC"}
    fallback = {
        "symbol": "BTC/USDT",
        "name": "Bitcoin",
        "price": "$60,000.00",
        "change_24h": "+0.00%",
        "is_up": True,
        "high_24h": "$61,000.00",
        "low_24h": "$59,000.00",
        "update_time": "00:00",
    }
    
    # 默认调用
    res = await dispatch_provider("crypto", mode_def, content_cfg, fallback)
    assert res is not None
    assert "price" in res
    assert "change_24h" in res
    assert "high_24h" in res
    assert "low_24h" in res
    assert "symbol" in res


def test_crypto_preview_endpoint():
    with TestClient(app) as client:
        resp = client.get("/api/preview?persona=CRYPTO&mode_override=%7B%22symbol%22%3A%22ETH%22%7D")
        assert resp.status_code == 200
        assert resp.headers.get("content-type") == "image/png"
        assert len(resp.content) > 1000
