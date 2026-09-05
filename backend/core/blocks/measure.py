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

    elif btype == "image":
        w = int(block.get("width", 220) * ctx.scale)
        h = int(block.get("height", 140) * ctx.scale)
        mb = int(block.get("margin_bottom", 6) * ctx.scale)
        return min(w, max_width), h + mb

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

    elif btype == "status_pill":
        text = str(ctx.get_field(block.get("field", "")) if block.get("field") else block.get("text", ""))
        text = ctx.resolve(text)
        font_size = int(block.get("font_size", 10) * ctx.scale)
        font = load_font("noto_serif_regular", font_size)
        bbox = font.getbbox(text)
        tw = bbox[2] - bbox[0]
        th = max(bbox[3] - bbox[1], font_size)
        dot_r = int(2.5 * ctx.scale) or 2
        pad_x = int(block.get("padding_x", 6) * ctx.scale)
        pad_y = int(block.get("padding_y", 2) * ctx.scale)
        dot_gap = int(4 * ctx.scale)
        w = pad_x * 2 + dot_r * 2 + dot_gap + tw
        h = th + pad_y * 2
        return w, h

    elif btype == "divider_ornament":
        margin_bottom = int(block.get("margin_bottom", 6) * ctx.scale)
        return max_width, int(10 * ctx.scale) + margin_bottom

    elif btype == "progress_ring":
        size = int(block.get("size", 64) * ctx.scale)
        margin_bottom = int(block.get("margin_bottom", 6) * ctx.scale)
        extra = int(14 * ctx.scale) if block.get("label") else 0
        return size, size + extra + margin_bottom

    elif btype == "header_banner":
        h = int(block.get("height", 34) * ctx.scale)
        margin_bottom = int(block.get("margin_bottom", 8) * ctx.scale)
        return max_width, h + margin_bottom

    elif btype == "header_compact":
        font_size = int(block.get("font_size", 14) * ctx.scale)
        extra = int(10 * ctx.scale) if block.get("line", True) else int(4 * ctx.scale)
        margin_bottom = int(block.get("margin_bottom", 6) * ctx.scale)
        return max_width, font_size + extra + margin_bottom

    elif btype in ("footer_ornate", "footer_badge"):
        return max_width, int(28 * ctx.scale)

    elif btype == "disaster_banner":
        h = int(block.get("height", 46) * ctx.scale)
        margin_bottom = int(block.get("margin_bottom", 8) * ctx.scale)
        return max_width, h + margin_bottom

    elif btype == "disaster_level_meter":
        h = int(block.get("height", 24) * ctx.scale)
        margin_bottom = int(block.get("margin_bottom", 10) * ctx.scale)
        return max_width, h + margin_bottom

    elif btype == "disaster_level_badge":
        return max_width, int(22 * ctx.scale)

    elif btype == "disaster_icon":
        sz = int(block.get("size", 44) * ctx.scale)
        margin_bottom = int(block.get("margin_bottom", 6) * ctx.scale)
        return sz, sz + margin_bottom

    elif btype == "corner_bracket":
        h = int(block.get("height", 80) * ctx.scale)
        margin_bottom = int(block.get("margin_bottom", 6) * ctx.scale)
        return max_width, h + margin_bottom

    elif btype == "double_border":
        h = int(block.get("height", 70) * ctx.scale)
        margin_bottom = int(block.get("margin_bottom", 8) * ctx.scale)
        return max_width, h + margin_bottom

    elif btype == "lace_border":
        return max_width, int(14 * ctx.scale)

    elif btype == "alert_callout":
        h = int(block.get("height", 32) * ctx.scale)
        mb = int(block.get("margin_bottom", 6) * ctx.scale)
        return max_width, h + mb

    elif btype == "change_diff_card":
        mb = int(block.get("margin_bottom", 6) * ctx.scale)
        return max_width, int(96 * ctx.scale) + mb

    elif btype == "timeline_event":
        mb = int(block.get("margin_bottom", 4) * ctx.scale)
        return max_width, int(18 * ctx.scale) + mb

    elif btype == "stat_progress_bar":
        font_size = int(block.get("font_size", 11) * ctx.scale)
        bar_h = max(4, int(block.get("height", 7) * ctx.scale))
        mb = int(block.get("margin_bottom", 6) * ctx.scale)
        return max_width, font_size + bar_h + 10 + mb

    elif btype == "pill_tag_list":
        mb = int(block.get("margin_bottom", 6) * ctx.scale)
        return max_width, int(26 * ctx.scale) + mb

    elif btype == "code_snippet_box":
        mb = int(block.get("margin_bottom", 6) * ctx.scale)
        return max_width, int(72 * ctx.scale) + mb

    elif btype == "two_column":
        left_blocks = block.get("left") or block.get("left_blocks") or []
        right_blocks = block.get("right") or block.get("right_blocks") or []
        gap = int(block.get("gap", 16) * ctx.scale)
        ratio = float(block.get("ratio") or block.get("left_ratio") or 0.5)
        _raw_mx = block.get("margin_x")
        margin_x = int(_raw_mx * ctx.scale) if _raw_mx is not None else int(ctx.screen_w * 0.06)

        col_avail = max_width - margin_x * 2 - gap
        left_w = int(col_avail * ratio)
        right_w = col_avail - left_w

        left_h = measure_column_blocks_height(ctx, left_blocks, x_offset=margin_x, available_width=left_w)
        right_h = measure_column_blocks_height(ctx, right_blocks, x_offset=margin_x + left_w + gap, available_width=right_w)
        max_h = max(left_h, right_h)
        mb = int(block.get("margin_bottom", 0) * ctx.scale)
        return max_width, max_h + mb

    elif btype == "qrcode":
        sz = int(block.get("size", 140) * ctx.scale)
        mb = int(block.get("margin_bottom", 6) * ctx.scale)
        return max_width, sz + mb

    elif btype in ("donut_chart", "bar_chart", "candlestick_chart", "area_chart"):
        h = int(block.get("height", 50) * ctx.scale)
        mb = int(block.get("margin_bottom", 6) * ctx.scale)
        return max_width, h + mb

    elif btype in ("drop_cap_paragraph", "poetic_couplet_box", "docker_container_card", "matrix_key_value_grid", "flight_boarding_pass"):
        mb = int(block.get("margin_bottom", 6) * ctx.scale)
        return max_width, int(34 * ctx.scale) + mb

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
