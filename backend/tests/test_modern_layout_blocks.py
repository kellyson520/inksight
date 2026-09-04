import pytest
import numpy as np
from PIL import Image, ImageDraw
from core.json_renderer import RenderContext, _render_block, _BLOCK_RENDERERS
from core.config import EINK_4COLOR_PALETTE
from scripts.inspect_render import analyze_image_layout


def test_registered_modern_blocks():
    assert "badge" in _BLOCK_RENDERERS
    assert "flex_row" in _BLOCK_RENDERERS
    assert "card" in _BLOCK_RENDERERS
    assert "grid" in _BLOCK_RENDERERS
    assert "metric_card" in _BLOCK_RENDERERS
    assert "striped_table" in _BLOCK_RENDERERS
    assert "segmented_row" in _BLOCK_RENDERERS
    assert "badge_group" in _BLOCK_RENDERERS


def test_render_badge_and_flex_row():
    img = Image.new("P", (400, 300), 1)
    img.putpalette(EINK_4COLOR_PALETTE)
    d = ImageDraw.Draw(img)
    ctx = RenderContext(
        draw=d, img=img,
        content={"price": "$248.50", "change": "+3.45%"},
        screen_w=400, screen_h=300, y=50, available_width=400, colors=3
    )

    flex_block = {
        "type": "flex_row",
        "justify": "center",
        "align_items": "center",
        "gap": 10,
        "items": [
            {"type": "text", "field": "price", "font_size": 28},
            {"type": "badge", "field": "change", "variant": "solid", "bg_color": "red", "color": "white", "radius": 6}
        ]
    }

    _render_block(ctx, flex_block)
    assert ctx.y > 50

    arr = np.array(img)
    red_pixels = (arr == 3)
    assert red_pixels.sum() > 50


def test_render_card_and_grid():
    img = Image.new("P", (400, 300), 1)
    img.putpalette(EINK_4COLOR_PALETTE)
    d = ImageDraw.Draw(img)
    ctx = RenderContext(
        draw=d, img=img,
        content={"title": "IoT Node", "temp": "24°C", "humi": "55%"},
        screen_w=400, screen_h=300, y=20, available_width=400, colors=3
    )

    card_block = {
        "type": "card",
        "border": "solid",
        "radius": 6,
        "padding": 10,
        "margin_x": 16,
        "children": [
            {"type": "text", "field": "title", "font_size": 16},
            {"type": "spacer", "height": 6},
            {
                "type": "grid",
                "columns": 2,
                "show_divider": True,
                "items": [
                    {"label": "温度", "field": "temp"},
                    {"label": "湿度", "field": "humi"}
                ]
            }
        ]
    }

    _render_block(ctx, card_block)
    assert ctx.y > 20

    metrics = analyze_image_layout(img)
    assert metrics["content_blocks_count"] >= 1
    overlaps = [g for g in metrics["gaps"] if g["status"] == "OVERLAP_COLLISION"]
    assert len(overlaps) == 0


def test_render_metric_card_and_segmented_row():
    img = Image.new("P", (400, 300), 1)
    img.putpalette(EINK_4COLOR_PALETTE)
    d = ImageDraw.Draw(img)
    ctx = RenderContext(
        draw=d, img=img,
        content={"power": "3.85", "state": "正常"},
        screen_w=400, screen_h=300, y=20, available_width=400, colors=3
    )

    m_card = {
        "type": "metric_card",
        "title": "今日实时功耗",
        "field": "power",
        "unit": "kW",
        "badge_field": "state",
        "badge_color": "red",
        "subtitle": "用电处于低谷期",
    }
    _render_block(ctx, m_card)
    assert ctx.y > 20

    seg = {
        "type": "segmented_row",
        "segments": 5,
        "active": 4,
        "active_color": "red",
    }
    _render_block(ctx, seg)
    assert ctx.y > 80


def test_render_striped_table_and_badge_group():
    img = Image.new("P", (400, 300), 1)
    img.putpalette(EINK_4COLOR_PALETTE)
    d = ImageDraw.Draw(img)
    ctx = RenderContext(
        draw=d, img=img,
        content={},
        screen_w=400, screen_h=300, y=20, available_width=400, colors=3
    )

    bg = {
        "type": "badge_group",
        "badges": [
            {"type": "badge", "text": "BTC", "variant": "solid", "bg_color": "red", "color": "white"},
            {"type": "badge", "text": "ETH", "variant": "outline", "bg_color": "black"},
            {"type": "badge", "text": "SOL", "variant": "outline", "bg_color": "black"},
        ]
    }
    _render_block(ctx, bg)
    assert ctx.y > 20

    table = {
        "type": "striped_table",
        "columns": [{"label": "资产", "key": "sym"}, {"label": "价格", "key": "price"}],
        "rows": [
            {"sym": "BTC", "price": "$80,800"},
            {"sym": "ETH", "price": "$2,500"},
        ]
    }
    _render_block(ctx, table)
    assert ctx.y > 60
