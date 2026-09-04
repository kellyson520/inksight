"""
边框与花边装饰组件模块 (Frames, Laces & Borders Blocks)
包含：lace_border, corner_bracket, double_border
"""
from __future__ import annotations

import logging
from typing import Any

from core.patterns.utils import (
    EINK_BG,
    EINK_FG,
    load_font,
    safe_font_bbox,
)
from .context import RenderContext
from .registry import register_block

logger = logging.getLogger(__name__)


@register_block("corner_bracket")
def render_corner_bracket(ctx: RenderContext, block: dict) -> None:
    """四角几何/直角包角装饰：绘制在当前可用区域四周，常用作重要公告或古典卡片外框。"""
    margin = int(block.get("margin", 8) * ctx.scale)
    bracket_len = int(block.get("bracket_length", 16) * ctx.scale)
    line_w = int(block.get("line_width", 2) * ctx.scale)
    color = ctx.resolve_color(block)

    x0 = ctx.x_offset + margin
    y0 = ctx.y + margin
    height = int(block.get("height", 80) * ctx.scale)
    x1 = ctx.x_offset + ctx.available_width - margin
    y1 = y0 + height

    # Top-Left
    ctx.draw.line([(x0, y0), (x0 + bracket_len, y0)], fill=color, width=line_w)
    ctx.draw.line([(x0, y0), (x0, y0 + bracket_len)], fill=color, width=line_w)

    # Top-Right
    ctx.draw.line([(x1, y0), (x1 - bracket_len, y0)], fill=color, width=line_w)
    ctx.draw.line([(x1, y0), (x1, y0 + bracket_len)], fill=color, width=line_w)

    # Bottom-Left
    ctx.draw.line([(x0, y1), (x0 + bracket_len, y1)], fill=color, width=line_w)
    ctx.draw.line([(x0, y1), (x0, y1 - bracket_len)], fill=color, width=line_w)

    # Bottom-Right
    ctx.draw.line([(x1, y1), (x1 - bracket_len, y1)], fill=color, width=line_w)
    ctx.draw.line([(x1, y1), (x1, y1 - bracket_len)], fill=color, width=line_w)

    # If children present or height reserved
    ctx.y = y1 + int(block.get("margin_bottom", 6) * ctx.scale)


@register_block("double_border")
def render_double_border(ctx: RenderContext, block: dict) -> None:
    """双重内外线边框：外粗内细或双细线，增强画面版式结构感。"""
    margin_x = int(block.get("margin_x", 8) * ctx.scale)
    gap = int(block.get("gap", 3) * ctx.scale)
    outer_w = int(block.get("outer_width", 2) * ctx.scale)
    inner_w = int(block.get("inner_width", 1) * ctx.scale)
    height = int(block.get("height", 70) * ctx.scale)
    color = ctx.resolve_color(block)

    x0 = ctx.x_offset + margin_x
    x1 = ctx.x_offset + ctx.available_width - margin_x
    y0 = ctx.y
    y1 = y0 + height

    # Outer rect
    ctx.draw.rectangle([(x0, y0), (x1, y1)], outline=color, width=outer_w)

    # Inner rect
    ix0 = x0 + gap + outer_w
    iy0 = y0 + gap + outer_w
    ix1 = x1 - gap - outer_w
    iy1 = y1 - gap - outer_w
    if ix1 > ix0 and iy1 > iy0:
        ctx.draw.rectangle([(ix0, iy0), (ix1, iy1)], outline=color, width=inner_w)

    ctx.y = y1 + int(block.get("margin_bottom", 8) * ctx.scale)


@register_block("lace_border")
def render_lace_border(ctx: RenderContext, block: dict) -> None:
    """墨水屏精美花边：支持齿状(teeth)、波浪(scallop)、回纹/虚线点(dots)。"""
    pattern = block.get("pattern", "teeth")  # "teeth", "scallop", "dots"
    margin_x = int(block.get("margin_x", 12) * ctx.scale)
    step = int(block.get("step", 10) * ctx.scale)
    line_w = int(block.get("line_width", 1) * ctx.scale)
    color = ctx.resolve_color(block)

    x_start = ctx.x_offset + margin_x
    x_end = ctx.x_offset + ctx.available_width - margin_x
    y = ctx.y + int(4 * ctx.scale)

    if pattern == "teeth":
        # 锯齿花边
        points = []
        cur_x = x_start
        up = True
        tooth_h = int(4 * ctx.scale)
        while cur_x < x_end:
            py = y - tooth_h if up else y + tooth_h
            points.append((cur_x, py))
            cur_x += max(4, step // 2)
            up = not up
        if len(points) >= 2:
            ctx.draw.line(points, fill=color, width=line_w)
    elif pattern == "scallop":
        # 连续半圆弧波浪
        r = max(3, step // 2)
        cur_x = x_start
        while cur_x + r * 2 <= x_end:
            ctx.draw.arc([(cur_x, y - r), (cur_x + r * 2, y + r)], start=0, end=180, fill=color, width=line_w)
            cur_x += r * 2
    else:  # dots
        # 点状珠串花边
        dot_r = max(1, int(2 * ctx.scale))
        cur_x = x_start
        while cur_x <= x_end:
            ctx.draw.ellipse([(cur_x - dot_r, y - dot_r), (cur_x + dot_r, y + dot_r)], fill=color)
            cur_x += step

    ctx.y = y + int(10 * ctx.scale)
