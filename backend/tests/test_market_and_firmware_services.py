"""
Unit tests for MarketService, Custom Stocks Persistence, and Firmware Service.
"""
import pytest
from core.market_service import MarketService
from core.firmware_service import (
    build_firmware_manifest,
    chip_family_from_asset_name,
    pick_firmware_asset,
    expand_firmware_release_assets,
)


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
