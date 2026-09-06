"""
Unit tests for MarketService, Custom Stocks Persistence, and Firmware Service.
"""
import json
import pytest
from core.market_service import MarketService
from core.firmware_service import (
    build_firmware_manifest,
    chip_family_from_asset_name,
    pick_firmware_asset,
    expand_firmware_release_assets,
    load_firmware_releases,
    validate_firmware_url,
)
from core.outbound_http import HttpResponse


def test_firmware_manifest_builder():
    manifest = build_firmware_manifest("1.2.0", "https://example.com/fw.bin", "ESP32-S3")
    assert manifest["name"] == "InkSight"
    assert manifest["version"] == "1.2.0"
    assert manifest["builds"][0]["chipFamily"] == "ESP32-S3"
    assert manifest["builds"][0]["parts"][0]["path"] == "https://example.com/fw.bin"


def test_chip_family_detection():
    assert chip_family_from_asset_name("inksight-firmware-esp32s3-v1.2.0.bin") == "ESP32-S3"
    assert chip_family_from_asset_name("inksight-firmware-esp32c3-v1.2.0.bin") == "ESP32-C3"
    assert chip_family_from_asset_name("firmware_wroom32e.bin") == "ESP32"


def test_pick_firmware_asset():
    assets = [
        {"name": "source.tar.gz"},
        {"name": "other-binary.bin"},
        {"name": "inksight-firmware-v1.0.0.bin"},
    ]
    picked = pick_firmware_asset(assets)
    assert picked is not None
    assert picked["name"] == "inksight-firmware-v1.0.0.bin"


def test_expand_firmware_release_assets():
    release = {
        "tag_name": "v1.2.0",
        "published_at": "2026-09-01T00:00:00Z",
        "assets": [
            {
                "name": "inksight-firmware-esp32s3.bin",
                "browser_download_url": "https://github.com/downloads/esp32s3.bin",
                "size": 1024000,
            }
        ],
    }
    expanded = expand_firmware_release_assets(release)
    assert len(expanded) == 1
    assert expanded[0]["version"] == "1.2.0"
    assert expanded[0]["chip_family"] == "ESP32-S3"
    assert expanded[0]["download_url"] == "https://github.com/downloads/esp32s3.bin"


@pytest.mark.asyncio
async def test_firmware_release_loader_uses_shared_outbound(monkeypatch):
    import core.firmware_service as firmware

    payload = [{"tag_name": "v1.0.0", "assets": []}]
    calls = []

    def fake_get_json(url, *, headers=None, policy=None):
        calls.append((url, headers))
        return HttpResponse(200, {}, json.dumps(payload).encode(), url, 1, 1.0)

    monkeypatch.setattr(firmware.outbound_http, "get_json", fake_get_json)
    firmware._firmware_release_cache["payload"] = None
    result = await load_firmware_releases(force_refresh=True)
    assert result["count"] == 0
    assert calls and calls[0][0] == firmware.GITHUB_RELEASES_API
    assert calls[0][1]["Accept"] == "application/vnd.github+json"


@pytest.mark.asyncio
async def test_firmware_url_validation_uses_shared_outbound(monkeypatch):
    import core.firmware_service as firmware

    calls = []

    def fake_head(url, *, headers=None, policy=None):
        calls.append(("head", url, policy))
        return HttpResponse(200, {"content-type": "application/octet-stream", "content-length": "12"}, b"", url, 1, 1.0)

    monkeypatch.setattr(firmware.outbound_http, "head", fake_head, raising=False)
    result = await validate_firmware_url("https://example.com/firmware.bin")
    assert result["ok"] is True
    assert calls and calls[0][0:2] == ("head", "https://example.com/firmware.bin")
    assert calls[0][2].follow_redirects is True


@pytest.mark.asyncio
async def test_firmware_url_validation_range_fallback_preserves_redirects(monkeypatch):
    import core.firmware_service as firmware

    calls = []

    def fake_head(url, *, headers=None, policy=None):
        raise ValueError("head unavailable")

    def fake_get(url, *, headers=None, policy=None):
        calls.append((url, headers, policy))
        return HttpResponse(200, {}, b"x", url, 1, 1.0)

    monkeypatch.setattr(firmware.outbound_http, "head", fake_head, raising=False)
    monkeypatch.setattr(firmware.outbound_http, "get_bytes", fake_get)
    result = await validate_firmware_url("https://example.com/firmware.bin")
    assert result["ok"] is True
    assert calls[0][1] == {"Range": "bytes=0-0"}
    assert calls[0][2].follow_redirects is True


@pytest.mark.asyncio
async def test_market_service_normalize_symbol():
    svc = MarketService()
    assert svc.normalize_symbol("btc/usdt") == "BTC"
    assert svc.normalize_symbol("aapl") == "AAPL"
    assert svc.normalize_symbol(" TSLA ") == "TSLA"


@pytest.mark.asyncio
async def test_market_service_custom_stock_lifecycle():
    svc = MarketService()
    # Add custom stock
    res = await svc.add_custom_stock("TEST_TICKER", "测试股票")
    assert res["symbol"] == "TEST_TICKER"
    assert res["name"] == "测试股票"

    all_stocks = svc.get_all_stocks()
    symbols = [s["symbol"] for s in all_stocks]
    assert "TEST_TICKER" in symbols

    # Remove custom stock
    removed = svc.remove_custom_stock("TEST_TICKER")
    assert removed is True
    all_stocks_after = svc.get_all_stocks()
    symbols_after = [s["symbol"] for s in all_stocks_after]
    assert "TEST_TICKER" not in symbols_after
