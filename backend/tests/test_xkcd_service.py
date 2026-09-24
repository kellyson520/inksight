import pytest
from unittest.mock import patch
from PIL import Image
from core.xkcd_service import get_daily_xkcd, _process_comic_image, _get_fallback_comic


def test_process_comic_image_produces_1bit_eink_image():
    # Create RGB test image
    test_img = Image.new("RGB", (600, 400), (255, 255, 255))
    processed = _process_comic_image(test_img, max_w=360, max_h=180)
    assert processed.mode == "1"
    assert processed.width <= 360
    assert processed.height <= 180


def test_xkcd_fallback_comic():
    comic = _get_fallback_comic()
    assert comic["num"] > 0
    assert "title" in comic
    assert "alt" in comic
    assert comic["source_status"] == "fallback"
    assert isinstance(comic.get("comic_image"), Image.Image)


@pytest.mark.asyncio
async def test_get_daily_xkcd_with_network_fallback():
    from core.xkcd_service import _XKCD_CACHE
    _XKCD_CACHE.clear()
    with patch("core.xkcd_service.outbound_http.get_json", side_effect=Exception("Network error")):
        comic = await get_daily_xkcd()
        assert comic["source_status"] == "fallback"
        assert comic["num"] > 0
        assert "title" in comic
