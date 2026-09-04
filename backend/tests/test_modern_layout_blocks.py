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


def test_render_badge_and_flex_row():
    # 使用墨水屏调色板模式 P
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
    # 验证红色调色板索引 (3) 存在 (badge)
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
    # 验证没有碰撞
    overlaps = [g for g in metrics["gaps"] if g["status"] == "OVERLAP_COLLISION"]
    assert len(overlaps) == 0
