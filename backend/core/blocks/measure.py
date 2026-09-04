"""
排版与块尺寸测量基础设施 (Block Size & Dimension Measurement)
提供不依赖假图渲染的高性能分析型尺寸测量。
"""
from __future__ import annotations

import logging
from typing import Any

from PIL import Image, ImageDraw

from core.patterns.utils import EINK_BG, has_cjk, load_font
from .context import RenderContext
from .registry import render_block
from .text import pick_cjk_font

logger = logging.getLogger(__name__)


def measure_block_size(ctx: RenderContext, block: dict, max_width: int) -> tuple[int, int]:
    """高性能计算 Block 的宽高，优先命中分析型快速路径。"""
    btype = block.get("type", "")
    if btype == "badge":
        field_name = block.get("field")
        text = str(ctx.get_field(field_name)) if field_name else ctx.resolve(block.get("template", block.get("text", "")))
        font_size = int(block.get("font_size", 12) * ctx.scale)
        font_key = block.get("font", "noto_serif_bold")
        if has_cjk(text):
            font_key = pick_cjk_font(font_key)
        font = load_font(font_key, font_size)
        bbox = font.getbbox(text)
        pad_x = int(block.get("padding_x", 8) * ctx.scale)
        pad_y = int(block.get("padding_y", 3) * ctx.scale)
        w = bbox[2] - bbox[0] + pad_x * 2
        h = max(bbox[3], font_size) + pad_y * 2
        return w, h

    elif btype in ("text", "centered_text"):
        text = str(ctx.get_field(block.get("field", "")) if block.get("field") else ctx.resolve(block.get("template", block.get("text", ""))))
        font_size = int(block.get("font_size", 14) * ctx.scale)
        font_key = block.get("font", "noto_serif_regular")
        if has_cjk(text):
            font_key = pick_cjk_font(font_key)
        font = load_font(font_key, font_size)
        bbox = font.getbbox(text)
        w = min(bbox[2] - bbox[0], max_width)
        line_height = int(block.get("line_height", font_size + 6) * ctx.scale) if block.get("line_height") else (font_size + 6)
        h = max(line_height, bbox[3])
        return w, h

    elif btype == "icon_text":
        text = str(ctx.get_field(block.get("field", "")) if block.get("field") else ctx.resolve(block.get("template", block.get("text", ""))))
        font_size = int(block.get("font_size", 14) * ctx.scale)
        icon_size = int(block.get("icon_size", 12) * ctx.scale)
        font = load_font(pick_cjk_font("noto_serif_regular") if has_cjk(text) else "noto_serif_regular", font_size)
        bbox = font.getbbox(text)
        w = icon_size + 4 + (bbox[2] - bbox[0])
        h = max(icon_size, font_size + 6)
        return w, h

    elif btype == "spacer":
        return max_width, int(block.get("height", 8) * ctx.scale)

    elif btype == "separator":
        return max_width, int(block.get("margin_bottom", 6) * ctx.scale) + 2

    elif btype == "grid":
        items = block.get("items", [])
        cols = max(1, int(block.get("columns", 2)))
        gap_y = int(block.get("gap_y", block.get("gap", 6)) * ctx.scale)
        font_size = int(block.get("font_size", 11) * ctx.scale)
        val_size = int(block.get("value_size", 13) * ctx.scale)
        row_count = (len(items) + cols - 1) // cols if items else 1
        row_h = font_size + val_size + 8
        margin_bottom = int(block.get("margin_bottom", 8) * ctx.scale)
        return max_width, row_count * (row_h + gap_y) + margin_bottom

    elif btype == "segmented_row":
        h = int(block.get("height", 6) * ctx.scale)
        margin_bottom = int(block.get("margin_bottom", 6) * ctx.scale)
        return max_width, h + margin_bottom

    else:
        measure_img = Image.new("1", (max(1, max_width), 100), EINK_BG)
        mc = RenderContext(
            draw=ImageDraw.Draw(measure_img),
            img=measure_img,
            content=ctx.content,
            screen_w=ctx.screen_w,
            screen_h=ctx.screen_h,
            y=0,
            x_offset=0,
            available_width=max_width,
            colors=ctx.colors,
        )
        render_block(mc, block)
        return max_width, max(1, mc.y)


def measure_column_blocks_height(ctx: RenderContext, blocks: list[dict], x_offset: int, available_width: int) -> int:
    """测量垂直子元素群落的总占用高度。"""
    measure_img = Image.new("1", (max(1, available_width), max(1, ctx.screen_h)), EINK_BG)
    mc = RenderContext(
        draw=ImageDraw.Draw(measure_img),
        img=measure_img,
        content=ctx.content,
        screen_w=ctx.screen_w,
        screen_h=ctx.screen_h,
        y=0,
        x_offset=x_offset,
        available_width=available_width,
        colors=ctx.colors,
        footer_height=0,
    )
    for b in blocks:
        render_block(mc, b)
    return mc.y
