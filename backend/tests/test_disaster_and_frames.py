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
        "disaster_hero",
        "disaster_publisher_bar",
    ]
    for b in new_blocks:
        assert b in BLOCK_RENDERERS, f"Block {b} must be registered in BLOCK_RENDERERS"


def test_render_disaster_hero_and_publisher_bar():
    img = Image.new("P", (400, 300), 1)
    img.putpalette(EINK_4COLOR_PALETTE)
    draw = ImageDraw.Draw(img)
    ctx = RenderContext(
        draw=draw,
        img=img,
        screen_w=400,
        screen_h=300,
        colors=3,
        x_offset=0,
        y=10,
        available_width=400,
        footer_height=24,
        content={"level": "红色", "type_name": "暴雨", "sender": "国家气象中心", "pub_time": "14:00"},
    )
    # 渲染 hero: 大图标与居中标题
    render_block(ctx, {"type": "disaster_hero", "hazard": "rainstorm", "type_name": "暴雨", "level": "红色", "icon_size": 60})
    assert ctx.y > 60

    # 渲染 publisher_bar: 最下层发布单位
    render_block(ctx, {"type": "disaster_publisher_bar", "sender": "国家气象中心", "time": "14:00"})
    assert ctx.y >= 260


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


def test_national_standard_warning_levels_hierarchy():
    from core.disaster_service import normalize_warning_level, STANDARD_WARNING_LEVELS

    # 1. 红色预警 (I级 / 特别严重)
    score1, meta1 = normalize_warning_level("红色")
    assert score1 == 1
    assert meta1["roman"] == "I级"
    assert meta1["severity_desc"] == "特别严重"

    # 2. 橙色预警 (II级 / 严重)
    score2, meta2 = normalize_warning_level("橙色预警")
    assert score2 == 2
    assert meta2["roman"] == "II级"
    assert meta2["severity_desc"] == "严重"

    # 3. 黄色预警 (III级 / 较重)
    score3, meta3 = normalize_warning_level("黄色")
    assert score3 == 3
    assert meta3["roman"] == "III级"
    assert meta3["severity_desc"] == "较重"

    # 4. 蓝色预警 (IV级 / 一般)
    score4, meta4 = normalize_warning_level("蓝色预警[IV级]")
    assert score4 == 4
    assert meta4["roman"] == "IV级"
    assert meta4["severity_desc"] == "一般"


def test_render_disaster_level_meter_all_levels():
    from core.json_renderer import render_json_mode

    levels = ["蓝色", "黄色", "橙色", "红色"]
    for lvl in levels:
        alert_dict = {
            "level": lvl,
            "type_name": "暴雨",
            "hazard_key": "rainstorm",
            "sender": "北京市气象台",
            "pub_time": "2026-09-04 17:00",
            "text": f"北京市发布暴雨{lvl}预警信号，请注意防范。",
        }
        mode_def = build_disaster_alert_mode_def(alert_dict)
        img = render_json_mode(
            mode_def,
            mode_def["content"],
            date_str="2026-09-04",
            weather_str="暴雨",
            battery_pct=90,
            screen_w=400,
            screen_h=300,
            colors=3,
        )
        assert img.size == (400, 300)
        rep = analyze_image_layout(img)
        assert rep["content_blocks_count"] >= 3
        for g in rep["gaps"]:
            assert g["status"] != "OVERLAP_COLLISION"

