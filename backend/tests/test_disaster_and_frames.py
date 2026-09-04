import pytest
import numpy as np
from PIL import Image, ImageDraw

from core.blocks import BLOCK_RENDERERS, RenderContext, render_block, measure_block_size
from core.config import EINK_4COLOR_PALETTE
from core.patterns.utils import EINK_BG, EINK_FG
from core.disaster_service import (
    simulate_disaster_alert,
    clear_simulated_alert,
    check_device_disaster_alert,
    build_disaster_alert_mode_def,
    fetch_active_alerts,
    LEVEL_SEVERITY,
)
from core.blocks.disaster import draw_disaster_vector_icon
from core.pipeline import generate_and_render
from scripts.inspect_render import analyze_image_layout


def test_registered_new_blocks_exist():
    new_blocks = [
        "header_banner",
        "header_compact",
        "footer_ornate",
        "footer_badge",
        "corner_bracket",
        "double_border",
        "lace_border",
        "disaster_icon",
        "disaster_banner",
        "disaster_advice_box",
    ]
    for b in new_blocks:
        assert b in BLOCK_RENDERERS, f"Block {b} must be registered in BLOCK_RENDERERS"


def test_render_all_12_disaster_icons():
    hazards = [
        "typhoon", "rainstorm", "blizzard", "gale", "extreme_heat", "cold_wave",
        "earthquake", "wildfire", "tsunami", "hail", "sandstorm", "fog"
    ]
    img = Image.new("P", (400, 300), 1)
    img.putpalette(EINK_4COLOR_PALETTE)
    draw = ImageDraw.Draw(img)

    for i, h in enumerate(hazards):
        cx = 30 + (i % 6) * 60
        cy = 50 + (i // 6) * 80
        draw_disaster_vector_icon(draw, h, cx, cy, size=36, color=EINK_FG, accent_color=2)

    arr = np.array(img)
    # Check that icons drew pixels on the canvas
    assert (arr != 1).sum() > 500


def test_render_header_footer_and_frames():
    w, h = 400, 300
    img = Image.new("P", (w, h), 1)
    img.putpalette(EINK_4COLOR_PALETTE)
    draw = ImageDraw.Draw(img)

    ctx = RenderContext(
        draw=draw,
        img=img,
        content={"title": "墨水屏美学", "status": "ONLINE", "label": "系统监控", "ver": "v2.0"},
        screen_w=w,
        screen_h=h,
        y=10,
        available_width=w,
        colors=3,
        footer_height=24,
    )

    # 1. Header Banner
    render_block(ctx, {
        "type": "header_banner",
        "title": "晨间新闻",
        "badge": "头条",
        "right_text": "08:30",
        "style": "inverted",
        "bg_color": "black",
        "height": 30,
    })

    # 2. Corner Bracket
    render_block(ctx, {
        "type": "corner_bracket",
        "height": 60,
        "line_width": 2,
    })

    # 3. Lace Border
    render_block(ctx, {
        "type": "lace_border",
        "pattern": "teeth",
    })

    # 4. Footer Ornate
    render_block(ctx, {
        "type": "footer_ornate",
        "label": "DAILY BRIEFING",
        "attribution": "2026-09-04",
        "ornament": "diamond",
    })

    arr = np.array(img)
    assert (arr != 1).sum() > 200


@pytest.mark.asyncio
async def test_disaster_alert_highest_priority_interruption():
    mac = "AA:BB:CC:DD:EE:99"
    try:
        # 1. Inject simulated disaster alert
        alert = simulate_disaster_alert(mac, {
            "level": "红色",
            "type_name": "台风",
            "hazard_key": "typhoon",
            "title": "台风红色预警",
            "text": "台风即将来袭，最大风力14级！",
        })

        # 2. Regular request for STOIC should be INTERRUPTED by DISASTER_ALERT!
        img, content = await generate_and_render(
            persona="STOIC",
            config={"disaster_alert": {"enabled": True, "min_level": "yellow"}},
            date_ctx={"date_str": "9月4日 周五", "time_str": "16:40"},
            weather={"weather_str": "晴 24°C"},
            battery_pct=85,
            screen_w=400,
            screen_h=300,
            mac=mac,
            colors=3,
        )

        assert content is not None
        assert "台风即将来袭" in str(content.get("text"))

        # Verify layout analysis: healthy gaps
        rep = analyze_image_layout(img)
        assert rep["content_blocks_count"] >= 3
        for g in rep["gaps"]:
            assert g["status"] != "OVERLAP_COLLISION", f"Gap collision detected: {g}"

    finally:
        clear_simulated_alert(mac)


@pytest.mark.asyncio
async def test_disaster_alert_api_endpoints():
    from unittest.mock import AsyncMock, patch, MagicMock
    from api.routes.device import simulate_device_disaster_alert, clear_device_disaster_alert
    from core.disaster_service import check_device_disaster_alert

    mac = "AA:BB:CC:DD:EE:88"
    mock_request = MagicMock()

    with patch("api.routes.device.ensure_web_or_device_access", new=AsyncMock(return_value={"mode": "admin"})):
        # 1. Simulate alert endpoint
        r1 = await simulate_device_disaster_alert(
            mac,
            mock_request,
            body={
                "level": "红色",
                "type_name": "暴雨",
                "hazard_key": "rainstorm",
                "title": "特大暴雨红色预警",
                "text": "特大暴雨红色预警，请立刻停止户外活动并避险！",
            }
        )
        assert r1["ok"] is True

        # 2. Check active alert
        active = await check_device_disaster_alert(mac, {"disaster_alert": {"enabled": True}})
        assert active is not None
        assert "特大暴雨" in active["title"]

        # 3. Clear simulated alert endpoint
        r2 = await clear_device_disaster_alert(mac, mock_request)
        assert r2["ok"] is True

        active_cleared = await check_device_disaster_alert(mac, {"disaster_alert": {"enabled": True}})
        assert active_cleared is None

    from core.db import close_all
    await close_all()
