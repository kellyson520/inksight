"""
页眉与页脚多样化高级样式模块 (Advanced Headers & Footers Blocks)
包含：header_banner, header_compact, footer_ornate, footer_badge
"""
from __future__ import annotations

import logging
from typing import Any

from core.patterns.utils import (
    EINK_BG,
    EINK_FG,
    has_cjk,
    load_font,
    load_font_by_name,
    load_icon,
    safe_font_bbox,
)
from .context import RenderContext
from .registry import register_block

logger = logging.getLogger(__name__)


def _draw_rounded_rect(draw, bbox, radius, fill=None, outline=None, width=1):
    try:
        draw.rounded_rectangle(bbox, radius=radius, fill=fill, outline=outline, width=width)
    except AttributeError:
        draw.rectangle(bbox, fill=fill, outline=outline, width=width)


@register_block("header_banner")
def render_header_banner(ctx: RenderContext, block: dict) -> None:
    """全宽/横幅样式的高级页眉，支持实心、反白、胶囊与带重音条风格。"""
    title = str(block.get("title") or ctx.resolve(block.get("title_template") or "") or "")
    badge = str(block.get("badge") or ctx.resolve(block.get("badge_template") or "") or "")
    right_text = str(block.get("right_text") or ctx.resolve(block.get("right_template") or "") or "")
    style = block.get("style", "solid")  # "solid", "outlined", "inverted", "accent_bar"
    bg_color = ctx.resolve_color({"color": block.get("bg_color", "black")})
    fg_color = ctx.resolve_color({"color": block.get("fg_color", "white") if style == "inverted" else "black"})

    font_size = int(block.get("font_size", 16) * ctx.scale)
    font_key = block.get("font", "noto_serif_bold")
    font_title = load_font(font_key, font_size)

    height = int(block.get("height", 34) * ctx.scale)
    y_start = ctx.y
    y_end = y_start + height
    x_start = ctx.x_offset + int(block.get("margin_x", 12) * ctx.scale)
    x_end = ctx.x_offset + ctx.available_width - int(block.get("margin_x", 12) * ctx.scale)
    corner_r = int(block.get("radius", 4) * ctx.scale)

    if style == "inverted":
        _draw_rounded_rect(ctx.draw, [(x_start, y_start), (x_end, y_end)], radius=corner_r, fill=bg_color)
    elif style == "outlined":
        _draw_rounded_rect(ctx.draw, [(x_start, y_start), (x_end, y_end)], radius=corner_r, outline=bg_color, width=int(2 * ctx.scale))
    elif style == "accent_bar":
        # 左侧竖直粗标条
        bar_w = int(4 * ctx.scale)
        ctx.draw.rectangle([(x_start, y_start), (x_start + bar_w, y_end)], fill=bg_color)
        x_start += bar_w + int(8 * ctx.scale)
        ctx.draw.line([(x_start, y_end), (x_end, y_end)], fill=EINK_FG, width=1)
    else:  # solid underline
        ctx.draw.line([(x_start, y_end), (x_end, y_end)], fill=EINK_FG, width=int(2 * ctx.scale))

    cur_x = x_start + int(8 * ctx.scale)
    content_cy = y_start + height // 2

    # 绘制左侧胶囊徽标 (Badge)
    if badge:
        b_font_size = max(10, int(11 * ctx.scale))
        b_font = load_font("noto_serif_bold", b_font_size)
        bb = safe_font_bbox(b_font, badge)
        bw, bh = bb[2] - bb[0], bb[3] - bb[1]
        bp_x, bp_y = int(6 * ctx.scale), int(3 * ctx.scale)
        badge_rect = [
            (cur_x, content_cy - bh // 2 - bp_y),
            (cur_x + bw + bp_x * 2, content_cy + bh // 2 + bp_y)
        ]
        b_bg = EINK_BG if style == "inverted" else bg_color
        b_fg = bg_color if style == "inverted" else EINK_BG
        _draw_rounded_rect(ctx.draw, badge_rect, radius=int(3 * ctx.scale), fill=b_bg)
        ctx.draw.text((cur_x + bp_x, content_cy - bh // 2 - bp_y + 1), badge, fill=b_fg, font=b_font)
        cur_x += bw + bp_x * 2 + int(8 * ctx.scale)

    # 绘制标题
    if title:
        tb = safe_font_bbox(font_title, title)
        th = tb[3] - tb[1]
        ctx.draw.text((cur_x, content_cy - th // 2 - 2), title, fill=fg_color, font=font_title)

    # 绘制右侧文本 (如更新时间、分类等)
    if right_text:
        r_font_size = max(10, int(11 * ctx.scale))
        r_font = load_font("inter_medium", r_font_size)
        rb = safe_font_bbox(r_font, right_text)
        rw, rh = rb[2] - rb[0], rb[3] - rb[1]
        rx = x_end - int(8 * ctx.scale) - rw
        ctx.draw.text((rx, content_cy - rh // 2), right_text, fill=fg_color, font=r_font)

    ctx.y = y_end + int(block.get("margin_bottom", 8) * ctx.scale)


@register_block("header_compact")
def render_header_compact(ctx: RenderContext, block: dict) -> None:
    """紧凑型页眉：小圆点/状态指示器 + 标题 + 右侧轻量状态。"""
    title = str(block.get("title") or ctx.resolve(block.get("title_template") or "") or "")
    status = str(block.get("status") or ctx.resolve(block.get("status_template") or "") or "")
    dot_color = ctx.resolve_color({"color": block.get("dot_color", "black")})
    show_line = block.get("line", True)

    font_size = int(block.get("font_size", 14) * ctx.scale)
    font = load_font(block.get("font", "noto_serif_bold"), font_size)
    status_font = load_font("inter_medium", max(10, int(11 * ctx.scale)))

    margin_x = int(block.get("margin_x", 12) * ctx.scale)
    x_start = ctx.x_offset + margin_x
    x_end = ctx.x_offset + ctx.available_width - margin_x
    y = ctx.y

    # 圆点指示器
    dot_r = int(3 * ctx.scale)
    ctx.draw.ellipse([(x_start, y + font_size // 2 - dot_r), (x_start + dot_r * 2, y + font_size // 2 + dot_r)], fill=dot_color)

    title_x = x_start + dot_r * 2 + int(6 * ctx.scale)
    ctx.draw.text((title_x, y), title, fill=EINK_FG, font=font)

    if status:
        sb = safe_font_bbox(status_font, status)
        sw = sb[2] - sb[0]
        ctx.draw.text((x_end - sw, y + 2), status, fill=EINK_FG, font=status_font)

    next_y = y + font_size + int(4 * ctx.scale)
    if show_line:
        ctx.draw.line([(x_start, next_y), (x_end, next_y)], fill=EINK_FG, width=1)
        next_y += int(6 * ctx.scale)

    ctx.y = next_y + int(block.get("margin_bottom", 6) * ctx.scale)


@register_block("footer_ornate")
def render_footer_ornate(ctx: RenderContext, block: dict) -> None:
    """典雅复古页脚：双细线 + 居中菱形/星形装饰 + 左右来源与日期文本。"""
    label = str(block.get("label") or ctx.resolve(block.get("label_template") or "") or "")
    attribution = str(block.get("attribution") or ctx.resolve(block.get("attribution_template") or "") or "")
    ornament = block.get("ornament", "diamond")  # "diamond", "star", "dots", "none"
    margin_x = int(block.get("margin_x", 12) * ctx.scale)

    x_left = ctx.x_offset + margin_x
    x_right = ctx.x_offset + ctx.available_width - margin_x
    cx = (x_left + x_right) // 2

    # 置底或当前 y
    target_y = ctx.footer_top - int(24 * ctx.scale)
    if target_y < ctx.y:
        target_y = ctx.y + int(4 * ctx.scale)

    # 绘制上方双细线
    ctx.draw.line([(x_left, target_y), (x_right, target_y)], fill=EINK_FG, width=1)
    ctx.draw.line([(x_left, target_y + 2), (x_right, target_y + 2)], fill=EINK_FG, width=1)

    # 居中花饰
    ornament_y = target_y + 1
    if ornament == "diamond":
        d_sz = int(4 * ctx.scale)
        ctx.draw.polygon([
            (cx, ornament_y - d_sz),
            (cx + d_sz, ornament_y),
            (cx, ornament_y + d_sz),
            (cx - d_sz, ornament_y),
        ], fill=ctx.resolve_color(block))
    elif ornament == "star":
        ctx.draw.text((cx - int(4 * ctx.scale), ornament_y - int(7 * ctx.scale)), "✦", fill=ctx.resolve_color(block), font=load_font("noto_serif_regular", 11))

    # 文本部分
    font_size = max(9, int(10 * ctx.scale))
    font = load_font("inter_medium", font_size)
    text_y = target_y + int(6 * ctx.scale)

    if label:
        ctx.draw.text((x_left, text_y), label, fill=EINK_FG, font=font)

    if attribution:
        ab = safe_font_bbox(font, attribution)
        aw = ab[2] - ab[0]
        ctx.draw.text((x_right - aw, text_y), attribution, fill=EINK_FG, font=font)

    ctx.y = text_y + font_size + int(4 * ctx.scale)


@register_block("footer_badge")
def render_footer_badge(ctx: RenderContext, block: dict) -> None:
    """胶囊微章页脚：左侧彩色/实心状态徽章，右侧技术栈/数据时间戳。"""
    badge = str(block.get("badge") or ctx.resolve(block.get("badge_template") or "") or "")
    text = str(block.get("text") or ctx.resolve(block.get("text_template") or "") or "")
    dot_color = ctx.resolve_color({"color": block.get("dot_color", "red")})
    margin_x = int(block.get("margin_x", 12) * ctx.scale)

    x_left = ctx.x_offset + margin_x
    x_right = ctx.x_offset + ctx.available_width - margin_x
    y_line = ctx.footer_top - int(20 * ctx.scale)
    if y_line < ctx.y:
        y_line = ctx.y + int(4 * ctx.scale)

    ctx.draw.line([(x_left, y_line), (x_right, y_line)], fill=EINK_FG, width=1)

    content_y = y_line + int(5 * ctx.scale)
    b_font = load_font("noto_serif_bold", max(9, int(10 * ctx.scale)))
    t_font = load_font("inter_medium", max(9, int(10 * ctx.scale)))

    cur_x = x_left
    if badge:
        bb = safe_font_bbox(b_font, badge)
        bw, bh = bb[2] - bb[0], bb[3] - bb[1]
        pill_rect = [(cur_x, content_y), (cur_x + bw + int(12 * ctx.scale), content_y + bh + int(4 * ctx.scale))]
        _draw_rounded_rect(ctx.draw, pill_rect, radius=int(3 * ctx.scale), fill=EINK_FG)
        ctx.draw.text((cur_x + int(6 * ctx.scale), content_y + 1), badge, fill=EINK_BG, font=b_font)
        cur_x += bw + int(18 * ctx.scale)

    # 圆点指示
    ctx.draw.ellipse([(cur_x, content_y + int(3 * ctx.scale)), (cur_x + int(5 * ctx.scale), content_y + int(8 * ctx.scale))], fill=dot_color)

    if text:
        tb = safe_font_bbox(t_font, text)
        tw = tb[2] - tb[0]
        ctx.draw.text((x_right - tw, content_y + 1), text, fill=EINK_FG, font=t_font)

    ctx.y = content_y + int(16 * ctx.scale)
