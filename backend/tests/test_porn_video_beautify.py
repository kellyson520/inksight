import pytest
from core.providers.porn_video_provider import _parse_porn_items, _build_video_fallback_image, generate_porn_video
from core.pipeline import generate_and_render
from PIL import Image

def test_parse_porn_items_extracts_duration_views_and_rating():
    raw_payload = {
        "videos": [
            {
                "title": "Stunning Beach Sunset Walk 4K",
                "username": "NatureVisuals",
                "duration": "15:20",
                "views": "125000",
                "rating": "96",
                "default_thumb": "https://example.com/thumb1.jpg",
                "url": "https://example.com/view_video.php?viewkey=ph12345",
            },
            {
                "title": "Tokyo Night Cyberpunk Street Tour",
                "uploader": "CityVlogger",
                "duration": 365,  # 365 seconds -> 06:05
                "views": 2500000,
                "rating": 98.5,
                "thumbs": [{"src": "https://example.com/thumb2.jpg"}],
                "url": "https://example.com/view_video.php?viewkey=ph67890",
            },
        ]
    }
    items = _parse_porn_items(raw_payload)
    assert len(items) == 2
    
    item1 = items[0]
    assert item1["title"] == "Stunning Beach Sunset Walk 4K"
    assert "NatureVisuals" in item1["subtitle"]
    assert item1["duration"] == "15:20"
    assert "12.5万" in item1["views_label"] or "125K" in item1["views_label"] or "125000" in item1["views_label"]
    assert "96%" in item1["rating_label"]
    assert item1["thumbnail_url"] == "https://example.com/thumb1.jpg"
    assert item1["fallback_image"] is not None  # Generated high-quality vector cover for offline fallback
    
    item2 = items[1]
    assert item2["title"] == "Tokyo Night Cyberpunk Street Tour"
    assert "06:05" in item2["duration"]
    assert "250万" in item2["views_label"] or "2.5M" in item2["views_label"]
    assert "98%" in item2["rating_label"]

def test_build_video_fallback_image_produces_clean_eink_card():
    im = _build_video_fallback_image(
        title="精选推荐视频",
        author="VerifiedCreator",
        duration="12:45",
        views_label="128万次播放",
        rating_label="98%好评",
        rank_label="NO.1",
        width=640,
        height=360,
    )
    assert isinstance(im, Image.Image)
    assert im.size == (640, 360)
    # Check that it has rich graphical contrast (not nearly empty or pitch black)
    # White background with black text/borders and orange accent
    data = list(im.getdata())
    light_px = sum(1 for p in data if sum(p[:3]) / 3 > 200)
    dark_px = sum(1 for p in data if sum(p[:3]) / 3 < 80)
    assert light_px > 50000, f"Expected clean light background, got {light_px}"
    assert dark_px > 3000, f"Expected readable dark borders and glyphs, got {dark_px}"

@pytest.mark.asyncio
async def test_porn_video_renders_cover_card_with_badges():
    # Test rendering PORN_VIDEO in cover_card mode
    img, content = await generate_and_render(
        "PORN_VIDEO",
        {"layout_style": "cover_card"},
        {"date_str": "9月11日", "time_str": "15:00:00"},
        {"weather_str": "晴 22℃"},
        100,
        400,
        300,
    )
    assert img is not None
    assert img.size == (400, 300)
    assert len(content.get("items", [])) > 0
    first_item = content["items"][0]
    assert "title" in first_item
    # Check that image_data or thumbnail was rendered
    assert first_item.get("image_data") is not None or first_item.get("thumbnail_url")
