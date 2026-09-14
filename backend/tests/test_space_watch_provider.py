import pytest
from unittest.mock import patch
from core.providers.space_watch_provider import (
    generate_space_watch,
    format_space_pass_data,
)
from core.pipeline import generate_and_render

def test_format_space_pass_data():
    data = format_space_pass_data(target="CSS", city="济南")
    assert data["target_name"] == "中国空间站 (天宫)"
    assert "km" in data["orbit_altitude"]
    assert "km/s" in data["orbit_velocity"]
    assert "°" in data["next_pass_elevation"]
    assert data["astronomy_event_title"]

@pytest.mark.asyncio
async def test_space_watch_provider_with_iss_override():
    cfg = {
        "mode_overrides": {
            "SPACE_WATCH": {
                "target": "ISS",
                "city": "北京",
            }
        }
    }
    data = await generate_space_watch(
        mode_def={"mode_id": "SPACE_WATCH"},
        content_cfg={"type": "computed", "provider": "space_watch"},
        fallback={"target_name": "天宫"},
        config=cfg,
    )
    assert "国际空间站" in data["target_name"]
    assert data["orbit_altitude"]
    assert data["next_pass_time"]

@pytest.mark.asyncio
async def test_space_watch_renders_crisp_eink_board():
    img, content = await generate_and_render(
        "SPACE_WATCH",
        {"target": "CSS"},
        {"date_str": "9月14日 周一", "time_str": "20:00:00"},
        {"weather_str": "晴 22℃"},
        100,
        400,
        300,
    )
    assert img is not None
    assert img.size == (400, 300)
    assert "天宫" in content.get("target_name", "")
    # 验证生成了充沛的墨水屏黑色像素点
    pixels = list(img.getdata())
    assert pixels.count(0) > 3000
