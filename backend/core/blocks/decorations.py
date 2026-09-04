"""
装饰元素与事件流组件模块 (Decorative & Event Stream Blocks)
包含：quote_card (优雅引言框), timeline (时间轴日程), divider_ornament (装饰分割线), status_pill (状态药丸微组件)
"""
from __future__ import annotations

import logging
from typing import Any

from core.patterns.utils import (
    EINK_BG,
    EINK_FG,
    draw_dashed_line,
    has_cjk,
    load_font,
    wrap_text,
)
from .context import RenderContext
from .registry import register_block
from .text import pick_cjk_font

logger = logging.getLogger(__name__)


def render_quote_card(ctx: RenderContext, block: dict) -> None:
    """渲染典雅的名言引言卡片，支持左侧重音竖条、可选外框与作者署名。"""
    q_text = str(ctx.get_field(block.get("quote_field", "")) if block.get("quote_field") else block.get("quote", block.get("text", "")))
    q_text = ctx.resolve(q_text)
    if not q_text:
        return

    author = str(ctx.get_field(block.get("author_field", "")) if block.get("author_field") else block.get("author", ""))
    author = ctx.resolve(author)
    category = str(block.get("category", ""))

    scale = ctx.scale
    margin_x = int(block.get("margin_x", 14) * scale)
    margin_bottom = int(block.get("margin_bottom", 8) * scale)
    card_style = block.get("style", "bar")  # "bar" | "box" | "minimal"
    font_size = int(block.get("font_size", 13) * scale)
    author_size = max(8, int(block.get("author_font_size", font_size - 2)))

    font_key = pick_cjk_font("noto_serif_regular") if has_cjk(q_text) else "lora_regular"
    author_font_key = pick_cjk_font("noto_serif_light") if has_cjk(author) else "lora_regular"
    q_font = load_font(font_key, font_size)
    a_font = load_font(author_font_key, author_size)

    avail_w = ctx.available_width - margin_x * 2
    pad_left = int(12 * scale) if card_style == "bar" else int(8 * scale)
    pad_right = int(8 * scale)
    pad_top = int(6 * scale)
    pad_bottom = int(6 * scale)
    content_w = avail_w - pad_left - pad_right

    lines = wrap_text(q_text, q_font, content_w)
    if not lines:
        lines = [q_text]

    line_h = font_size + int(4 * scale)
    quote_h = len(lines) * line_h
    total_h = pad_top + quote_h + pad_bottom
    if author:
        total_h += author_size + int(4 * scale)

    start_x = ctx.x_offset + margin_x
    start_y = ctx.y

    bar_color_name = block.get("bar_color", "red" if ctx.colors >= 3 else "black")
    bar_color = ctx.color_index(bar_color_name, default=EINK_FG)

    if card_style == "box":
        ctx.draw.rounded_rectangle([start_x, start_y, start_x + avail_w, start_y + total_h], radius=4, outline=EINK_FG, width=1)
    elif card_style == "bar":
        # 3px 粗重音竖条
        ctx.draw.rectangle([start_x, start_y + 2, start_x + max(2, int(3 * scale)), start_y + total_h - 2], fill=bar_color)

    # 绘制引言正文
    cur_y = start_y + pad_top
    text_x = start_x + pad_left
    text_color = ctx.color_index(block.get("color", "black"), default=EINK_FG)

    for line in lines:
        ctx.draw.text((text_x, cur_y), line, fill=text_color, font=q_font)
        cur_y += line_h

    # 绘制右对齐作者署名
    if author:
        cur_y += int(2 * scale)
        author_str = f"— {author}"
        abox = a_font.getbbox(author_str)
        aw = abox[2] - abox[0]
        ax = start_x + avail_w - pad_right - aw
        ctx.draw.text((ax, cur_y), author_str, fill=EINK_FG, font=a_font)

    ctx.y = start_y + total_h + margin_bottom


def render_timeline(ctx: RenderContext, block: dict) -> None:
    """渲染垂直时间轴日程事件流组件。"""
    raw_items = ctx.get_field(block.get("items_field", "timeline")) if block.get("items_field") else block.get("items", [])
    if not isinstance(raw_items, list) or not raw_items:
        return

    scale = ctx.scale
    margin_x = int(block.get("margin_x", 14) * scale)
    margin_bottom = int(block.get("margin_bottom", 8) * scale)
    bullet_size = int(block.get("bullet_size", 6) * scale) or 4
    time_col_w = int(block.get("time_width", 54) * scale)

    start_x = ctx.x_offset + margin_x
    spine_x = start_x + time_col_w + bullet_size + int(4 * scale)
    content_x = spine_x + bullet_size + int(6 * scale)
    content_max_w = ctx.available_width - margin_x * 2 - (content_x - start_x)

    font_time = load_font("noto_serif_light", int(10 * scale))
    font_title = load_font("noto_serif_bold", int(11 * scale))
    font_desc = load_font("noto_serif_light", int(10 * scale))

    accent_color = ctx.color_index(block.get("accent_color", "red" if ctx.colors >= 3 else "black"), default=EINK_FG)

    first_y = ctx.y
    cur_y = first_y
    node_centers: list[int] = []

    for idx, it in enumerate(raw_items):
        if not isinstance(it, dict):
            continue
        if cur_y >= ctx.footer_top - 12:
            break

        time_lbl = str(it.get("time", ""))
        title = str(it.get("title", ""))
        desc = str(it.get("desc", ""))
        is_active = bool(it.get("active", False))

        item_top_y = cur_y
        center_node_y = item_top_y + int(6 * scale)
        node_centers.append(center_node_y)

        # 1. 绘制时间标签
        if time_lbl:
            tbox = font_time.getbbox(time_lbl)
            tw = tbox[2] - tbox[0]
            ctx.draw.text((start_x + time_col_w - tw, item_top_y), time_lbl, fill=EINK_FG, font=font_time)

        # 2. 绘制节点圆点
        r = bullet_size // 2
        if is_active:
            ctx.draw.ellipse([spine_x - r - 1, center_node_y - r - 1, spine_x + r + 1, center_node_y + r + 1], fill=accent_color)
        else:
            ctx.draw.ellipse([spine_x - r, center_node_y - r, spine_x + r, center_node_y + r], fill=EINK_BG)
            ctx.draw.ellipse([spine_x - r, center_node_y - r, spine_x + r, center_node_y + r], outline=EINK_FG, width=1)

        # 3. 绘制标题与描述
        if title:
            ctx.draw.text((content_x, item_top_y), title, fill=accent_color if is_active else EINK_FG, font=font_title)
            cur_y += int(14 * scale)

        if desc:
            lines = wrap_text(desc, font_desc, content_max_w)
            for dl in lines[:2]:
                ctx.draw.text((content_x, cur_y), dl, fill=EINK_FG, font=font_desc)
                cur_y += int(12 * scale)

        cur_y += int(6 * scale)

    # 绘制贯穿节点的脊柱连线
    if len(node_centers) >= 2:
        ctx.draw.line([(spine_x, node_centers[0]), (spine_x, node_centers[-1])], fill=EINK_FG, width=1)

    ctx.y = cur_y + margin_bottom


def render_divider_ornament(ctx: RenderContext, block: dict) -> None:
    """渲染带居中装饰物（星形、菱形、圆点或短文）的对称分隔条。"""
    scale = ctx.scale
    margin_x = int(block.get("margin_x", 20) * scale)
    margin_bottom = int(block.get("margin_bottom", 6) * scale)
    ornament = block.get("ornament", "diamond")  # "diamond" | "circle" | "dots" | "text"
    center_text = str(block.get("text", ""))

    width = ctx.available_width - margin_x * 2
    x0 = ctx.x_offset + margin_x
    mid_x = x0 + width // 2
    mid_y = ctx.y + int(4 * scale)

    ornament_w = int(24 * scale)
    if ornament == "text" and center_text:
        font = load_font("noto_serif_light", int(9 * scale))
        bbox = font.getbbox(center_text)
        tw = bbox[2] - bbox[0]
        ornament_w = tw + int(12 * scale)
        ctx.draw.text((mid_x - tw // 2, mid_y - (bbox[3] - bbox[1]) // 2), center_text, fill=EINK_FG, font=font)
    elif ornament == "diamond":
        sz = int(4 * scale) or 3
        ctx.draw.polygon([(mid_x, mid_y - sz), (mid_x + sz, mid_y), (mid_x, mid_y + sz), (mid_x - sz, mid_y)], fill=EINK_FG)
    elif ornament == "circle":
        r = int(2.5 * scale) or 2
        ctx.draw.ellipse([mid_x - r, mid_y - r, mid_x + r, mid_y + r], fill=EINK_FG)
    elif ornament == "dots":
        r = 1
        for offset in (-6, 0, 6):
            ctx.draw.ellipse([mid_x + offset - r, mid_y - r, mid_x + offset + r, mid_y + r], fill=EINK_FG)

    # 两侧翼线
    half_line_gap = ornament_w // 2
    ctx.draw.line([(x0, mid_y), (mid_x - half_line_gap, mid_y)], fill=EINK_FG, width=1)
    ctx.draw.line([(mid_x + half_line_gap, mid_y), (x0 + width, mid_y)], fill=EINK_FG, width=1)

    ctx.y = mid_y + int(6 * scale) + margin_bottom


def render_status_pill(ctx: RenderContext, block: dict) -> None:
    """渲染带圆点指示器的紧凑状态药丸组件 (如 🟢 在线 / 🔴 异常 / 实时监控)。"""
    scale = ctx.scale
    text = str(ctx.get_field(block.get("field", "")) if block.get("field") else block.get("text", ""))
    text = ctx.resolve(text)
    if not text:
        return

    font_size = int(block.get("font_size", 10) * scale)
    font = load_font("noto_serif_regular", font_size)
    bbox = font.getbbox(text)
    tw = bbox[2] - bbox[0]
    th = max(bbox[3] - bbox[1], font_size)

    dot_r = int(2.5 * scale) or 2
    pad_x = int(block.get("padding_x", 6) * scale)
    pad_y = int(block.get("padding_y", 2) * scale)
    dot_gap = int(4 * scale)

    pill_w = pad_x * 2 + dot_r * 2 + dot_gap + tw
    pill_h = th + pad_y * 2
    radius = pill_h // 2

    align = block.get("align", "left")
    margin_x = int(block.get("margin_x", 0) * scale)
    margin_bottom = int(block.get("margin_bottom", 6) * scale)

    if align == "center":
        bx = ctx.x_offset + (ctx.available_width - pill_w) // 2
    elif align == "right":
        bx = ctx.x_offset + ctx.available_width - pill_w - margin_x
    else:
        bx = ctx.x_offset + margin_x

    by = ctx.y
    # 外围胶囊
    ctx.draw.rounded_rectangle([bx, by, bx + pill_w, by + pill_h], radius=radius, outline=EINK_FG, width=1)

    # 指示圆点
    dot_color_name = block.get("dot_color", "red" if ctx.colors >= 3 else "black")
    dot_fill = ctx.color_index(dot_color_name, default=EINK_FG)
    dot_cx = bx + pad_x + dot_r
    dot_cy = by + pill_h // 2
    ctx.draw.ellipse([dot_cx - dot_r, dot_cy - dot_r, dot_cx + dot_r, dot_cy + dot_r], fill=dot_fill)

    # 状态文字
    tx = dot_cx + dot_r + dot_gap
    ty = by + pad_y - bbox[1]
    ctx.draw.text((tx, ty), text, fill=EINK_FG, font=font)

    ctx.y = by + pill_h + margin_bottom


# 注册所有装饰与事件流类组件
register_block("quote_card", render_quote_card)
register_block("timeline", render_timeline)
register_block("divider_ornament", render_divider_ornament)
register_block("status_pill", render_status_pill)
