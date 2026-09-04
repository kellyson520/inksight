import pytest
import numpy as np
from PIL import Image, ImageDraw
from core.json_renderer import RenderContext, _render_block, _BLOCK_RENDERERS
from core.config import EINK_4COLOR_PALETTE
from scripts.inspect_render import analyze_image_layout


def test_registered_extended_blocks():
    for b in ("quote_card", "timeline", "divider_ornament", "status_pill", "gauge", "progress_ring", "kpi_diff"):
        assert b in _BLOCK_RENDERERS, f"Block {b} should be registered in _BLOCK_RENDERERS"


def test_render_quote_card():
    img = Image.new("P", (400, 300), 1)
    img.putpalette(EINK_4COLOR_PALETTE)
    d = ImageDraw.Draw(img)
    ctx = RenderContext(
        draw=d, img=img,
        content={"quote": "Stay hungry, stay foolish.", "author": "Steve Jobs"},
        screen_w=400, screen_h=300, y=30, available_width=400, colors=3
    )

    quote_block = {
        "type": "quote_card",
        "quote_field": "quote",
        "author_field": "author",
        "style": "bar",
        "bar_color": "red",
        "font_size": 14,
    }

    _render_block(ctx, quote_block)
    assert ctx.y > 60

    arr = np.array(img)
    red_pixels = (arr == 3)
    assert red_pixels.sum() > 20  # red bar pixels


def test_render_timeline():
    img = Image.new("P", (400, 300), 1)
    img.putpalette(EINK_4COLOR_PALETTE)
    d = ImageDraw.Draw(img)
    ctx = RenderContext(
        draw=d, img=img,
        content={
            "schedule": [
                {"time": "09:00", "title": "Morning Standup", "desc": "Sprint review", "active": False},
                {"time": "14:00", "title": "System Architecture", "desc": "Review core modular blocks", "active": True},
                {"time": "17:30", "title": "Wrapup & Deploy", "desc": "Production verification", "active": False},
            ]
        },
        screen_w=400, screen_h=300, y=20, available_width=400, colors=3
    )

    timeline_block = {
        "type": "timeline",
        "items_field": "schedule",
        "accent_color": "red",
    }

    _render_block(ctx, timeline_block)
    assert ctx.y > 100

    arr = np.array(img)
    red_pixels = (arr == 3)
    assert red_pixels.sum() > 10  # active node highlight


def test_render_divider_ornament_and_status_pill():
    img = Image.new("P", (400, 300), 1)
    img.putpalette(EINK_4COLOR_PALETTE)
    d = ImageDraw.Draw(img)
    ctx = RenderContext(
        draw=d, img=img,
        content={"status_text": "Live 监控中"},
        screen_w=400, screen_h=300, y=20, available_width=400, colors=3
    )

    pill_block = {
        "type": "status_pill",
        "field": "status_text",
        "align": "center",
        "dot_color": "red",
    }
    _render_block(ctx, pill_block)
    assert ctx.y > 35

    div_block = {
        "type": "divider_ornament",
        "ornament": "diamond",
    }
    _render_block(ctx, div_block)
    assert ctx.y > 55

    arr = np.array(img)
    assert (arr == 3).sum() > 5  # red dot in pill


def test_render_gauge_and_progress_ring():
    img = Image.new("P", (400, 300), 1)
    img.putpalette(EINK_4COLOR_PALETTE)
    d = ImageDraw.Draw(img)
    ctx = RenderContext(
        draw=d, img=img,
        content={"cpu_usage": 72.5, "mem_pct": 68},
        screen_w=400, screen_h=300, y=20, available_width=400, colors=3
    )

    gauge_block = {
        "type": "gauge",
        "field": "cpu_usage",
        "min": 0,
        "max": 100,
        "unit": "%",
        "title": "CPU 负载",
        "color": "red",
    }
    _render_block(ctx, gauge_block)
    y_after_gauge = ctx.y
    assert y_after_gauge > 50

    ring_block = {
        "type": "progress_ring",
        "field": "mem_pct",
        "label": "Memory",
        "color": "red",
    }
    _render_block(ctx, ring_block)
    assert ctx.y > y_after_gauge + 40


def test_render_kpi_diff():
    img = Image.new("P", (400, 300), 1)
    img.putpalette(EINK_4COLOR_PALETTE)
    d = ImageDraw.Draw(img)
    ctx = RenderContext(
        draw=d, img=img,
        content={"kpi_val": "$84,210", "kpi_diff": "+12.4%"},
        screen_w=400, screen_h=300, y=30, available_width=400, colors=3
    )

    kpi_block = {
        "type": "kpi_diff",
        "title": "24H 成交总额",
        "field": "kpi_val",
        "diff_field": "kpi_diff",
        "trend": "up",
        "align": "left",
    }
    _render_block(ctx, kpi_block)
    assert ctx.y > 60

    arr = np.array(img)
    # Check that pixels are drawn
    assert (arr != 1).sum() > 100
