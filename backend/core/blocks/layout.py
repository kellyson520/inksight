"""
结构容器与弹性排版组件模块 (Structural & Layout Blocks)
包含：separator, section, vertical_stack, conditional, spacer, two_column, group, flex_row, card
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
    load_icon,
)
from .context import RenderContext, section_icon_from_label, strip_emoji
from .measure import measure_block_size, measure_column_blocks_height
from .registry import register_block, render_block
from .text import pick_cjk_font

logger = logging.getLogger(__name__)


def _num(v: Any) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def render_separator(ctx: RenderContext, block: dict) -> None:
    style = block.get("style", "solid")
    margin_x = block.get("margin_x")
    if margin_x is not None:
        margin_x = int(margin_x * ctx.scale)
    else:
        margin_x = int(ctx.screen_w * 0.06)
    line_width = block.get("line_width", 1)

    color = ctx.resolve_color(block)
    if style == "short":
        w = int(block.get("width", 60) * ctx.scale)
        x0 = ctx.x_offset + (ctx.available_width - w) // 2
        ctx.draw.line([(x0, ctx.y), (x0 + w, ctx.y)], fill=color, width=line_width)
    elif style == "dashed":
        draw_dashed_line(ctx.draw, (ctx.x_offset + margin_x, ctx.y), (ctx.x_offset + ctx.available_width - margin_x, ctx.y),
                         fill=color, width=line_width)
    else:
        ctx.draw.line([(ctx.x_offset + margin_x, ctx.y), (ctx.x_offset + ctx.available_width - margin_x, ctx.y)],
                      fill=color, width=line_width)
    ctx.y += 8 + line_width


def render_section(ctx: RenderContext, block: dict) -> None:
    raw_title = block.get("title") or block.get("label", "")
    icon_name = block.get("icon")
    if not icon_name:
        icon_name = section_icon_from_label(raw_title)
    title = strip_emoji(raw_title)
    title_font_key = block.get("title_font", "noto_serif_regular")
    title_font_size = int(block.get("title_font_size", 14) * ctx.scale)

    if has_cjk(title):
        title_font_key = pick_cjk_font(title_font_key)
    font = load_font(title_font_key, title_font_size)

    margin_x = int(ctx.screen_w * 0.06)
    x = ctx.x_offset + margin_x
    icon_size = int(12 * ctx.scale)
    if icon_name:
        icon_img = load_icon(icon_name, size=(icon_size, icon_size))
        if icon_img:
            ctx.paste_icon(icon_img, (x, ctx.y))
            x += int(16 * ctx.scale)

    ctx.draw.text((x, ctx.y), title, fill=ctx.resolve_color(block), font=font)
    ctx.y += title_font_size + int(6 * ctx.scale)

    for child in block.get("children") or block.get("blocks", []):
        if ctx.y >= ctx.footer_top - 10:
            break
        render_block(ctx, child)

    mb = block.get("margin_bottom")
    if mb is not None:
        ctx.y += int(mb * ctx.scale)


def render_vertical_stack(ctx: RenderContext, block: dict) -> None:
    spacing = block.get("spacing", 0)
    for child in block.get("children", []):
        if ctx.y >= ctx.footer_top - 10:
            break
        render_block(ctx, child)
        ctx.y += spacing


def render_conditional(ctx: RenderContext, block: dict) -> None:
    field_name = block.get("field", "")
    value = ctx.get_field(field_name)
    conditions = block.get("conditions", [])

    for cond in conditions:
        op = cond.get("op", "exists")
        cmp_val = cond.get("value")
        matched = False

        if op == "exists":
            matched = bool(value)
        elif op == "eq":
            matched = value == cmp_val
        elif op == "gt":
            matched = _num(value) > _num(cmp_val)
        elif op == "lt":
            matched = _num(value) < _num(cmp_val)
        elif op == "gte":
            matched = _num(value) >= _num(cmp_val)
        elif op == "lte":
            matched = _num(value) <= _num(cmp_val)
        elif op == "len_eq":
            matched = isinstance(value, (list, str)) and len(value) == _num(cmp_val)
        elif op == "len_gt":
            matched = isinstance(value, (list, str)) and len(value) > _num(cmp_val)

        if matched:
            for child in cond.get("children", []):
                render_block(ctx, child)
            return

    for child in block.get("fallback_children", []):
        render_block(ctx, child)


def render_spacer(ctx: RenderContext, block: dict) -> None:
    if block.get("height_px") is not None:
        try:
            ctx.y += max(0, int(block["height_px"]))
        except (TypeError, ValueError):
            ctx.y += 0
        return
    try:
        h = float(block.get("height", 12))
    except (TypeError, ValueError):
        h = 12.0
    ctx.y += max(0, int(round(h * ctx.scale)))


def render_two_column(ctx: RenderContext, block: dict) -> None:
    left_blocks = block.get("left") or block.get("left_blocks") or []
    right_blocks = block.get("right") or block.get("right_blocks") or []
    gap = int(block.get("gap", 16) * ctx.scale)
    ratio = float(block.get("ratio") or block.get("left_ratio") or 0.5)

    _raw_mx = block.get("margin_x")
    if _raw_mx is not None:
        margin_x = int(_raw_mx * ctx.scale)
    else:
        margin_x = int(ctx.screen_w * 0.06)

    # 窄屏或可用宽度不足时优雅退化为单列流式布局
    col_avail = ctx.available_width - margin_x * 2 - gap
    if ctx.available_width < 250 or col_avail < 40:
        for b in left_blocks:
            render_block(ctx, b)
        for b in right_blocks:
            render_block(ctx, b)
        return

    left_w = int(col_avail * ratio)
    right_w = col_avail - left_w

    start_y = ctx.y
    left_x = ctx.x_offset + margin_x
    right_x = left_x + left_w + gap

    left_h = measure_column_blocks_height(ctx, left_blocks, x_offset=left_x, available_width=left_w)
    right_h = measure_column_blocks_height(ctx, right_blocks, x_offset=right_x, available_width=right_w)
    max_h = max(left_h, right_h)

    left_align = block.get("left_align_y", "top")
    right_align = block.get("right_align_y", "top")

    left_y = start_y
    if left_align == "center":
        left_y += max(0, (max_h - left_h) // 2)
    elif left_align in {"bottom", "end"}:
        left_y += max(0, max_h - left_h)

    right_y = start_y
    if right_align == "center":
        right_y += max(0, (max_h - right_h) // 2)
    elif right_align in {"bottom", "end"}:
        right_y += max(0, max_h - right_h)

    left_ctx = RenderContext(
        draw=ctx.draw, img=ctx.img, content=ctx.content,
        screen_w=ctx.screen_w, screen_h=ctx.screen_h,
        y=left_y, x_offset=left_x, available_width=left_w,
        colors=ctx.colors, footer_height=ctx.footer_height,
        footer_top_offset=ctx.footer_top_offset,
    )
    for b in left_blocks:
        if left_ctx.y >= ctx.footer_top - 4:
            break
        render_block(left_ctx, b)

    right_ctx = RenderContext(
        draw=ctx.draw, img=ctx.img, content=ctx.content,
        screen_w=ctx.screen_w, screen_h=ctx.screen_h,
        y=right_y, x_offset=right_x, available_width=right_w,
        colors=ctx.colors, footer_height=ctx.footer_height,
        footer_top_offset=ctx.footer_top_offset,
    )
    for b in right_blocks:
        if right_ctx.y >= ctx.footer_top - 4:
            break
        render_block(right_ctx, b)

    ctx.y = start_y + max_h
    mb = block.get("margin_bottom")
    if mb is not None:
        ctx.y += int(mb * ctx.scale)


def render_group(ctx: RenderContext, block: dict) -> None:
    title = block.get("title", "")
    if title:
        title_font_size = int(block.get("title_font_size", 12) * ctx.scale)
        title_font = load_font("noto_serif_bold", title_font_size)
        _raw_margin = block.get("margin_x")
        if _raw_margin is not None:
            margin_x = int(_raw_margin * ctx.scale)
        else:
            margin_x = int(ctx.available_width * 0.06)
        ctx.draw.text((ctx.x_offset + margin_x, ctx.y), title, fill=EINK_FG, font=title_font)
        ctx.y += title_font_size + int(4 * ctx.scale)
    for child in block.get("children", []):
        render_block(ctx, child)


def render_flex_row(ctx: RenderContext, block: dict) -> None:
    items = block.get("items", [])
    if not items or not isinstance(items, list):
        return

    margin_x = int(block.get("margin_x", 0) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 8) * ctx.scale)
    gap = int(block.get("gap", 8) * ctx.scale)
    justify = block.get("justify", "center")
    align_items = block.get("align_items", "center")

    avail_w = max(10, ctx.available_width - margin_x * 2)

    sizes = []
    for item in items:
        w, h = measure_block_size(ctx, item, avail_w)
        sizes.append((w, h))

    total_items_w = sum(s[0] for s in sizes)
    row_h = max(s[1] for s in sizes) if sizes else 0
    k = len(items)

    if justify == "space-between" and k > 1:
        computed_gap = max(0, (avail_w - total_items_w) // (k - 1))
        start_x = ctx.x_offset + margin_x
    elif justify == "left":
        computed_gap = gap
        start_x = ctx.x_offset + margin_x
    elif justify == "right":
        computed_gap = gap
        total_w = total_items_w + (k - 1) * gap
        start_x = ctx.x_offset + ctx.available_width - margin_x - total_w
    else:
        computed_gap = gap
        total_w = total_items_w + (k - 1) * gap
        start_x = ctx.x_offset + (ctx.available_width - total_w) // 2

    row_y = ctx.y
    cur_x = start_x

    for idx, (item, (w, h)) in enumerate(zip(items, sizes)):
        if align_items == "bottom":
            item_y = row_y + (row_h - h)
        elif align_items == "top":
            item_y = row_y
        else:
            item_y = row_y + (row_h - h) // 2

        btype = item.get("type", "")
        if btype in ("text", "centered_text"):
            text = str(ctx.get_field(item.get("field", "")) if item.get("field") else ctx.resolve(item.get("template", item.get("text", ""))))
            font_size = int(item.get("font_size", 14) * ctx.scale)
            font_key = item.get("font", "noto_serif_regular")
            if has_cjk(text):
                font_key = pick_cjk_font(font_key)
            font = load_font(font_key, font_size)
            bbox = font.getbbox(text)
            color = ctx.color_index(item.get("color", "black"), default=EINK_FG)
            ctx.draw.text((cur_x - bbox[0], item_y - bbox[1] + (h - (bbox[3] - bbox[1])) // 2), text, fill=color, font=font)
        else:
            item_ctx = RenderContext(
                draw=ctx.draw, img=ctx.img, content=ctx.content,
                screen_w=ctx.screen_w, screen_h=ctx.screen_h,
                y=item_y, x_offset=cur_x, available_width=w,
                colors=ctx.colors, footer_height=ctx.footer_height,
                footer_top_offset=ctx.footer_top_offset,
            )
            item_copy = dict(item)
            item_copy["margin_x"] = 0
            item_copy["margin_bottom"] = 0
            render_block(item_ctx, item_copy)

        cur_x += w + computed_gap

    ctx.y = row_y + row_h + margin_bottom


def render_card(ctx: RenderContext, block: dict) -> None:
    children = block.get("children", [])
    if not children:
        return

    scale = ctx.scale
    margin_x = int(block.get("margin_x", 12) * scale)
    margin_bottom = int(block.get("margin_bottom", 8) * scale)
    padding = int(block.get("padding", 8) * scale)
    radius = int(block.get("radius", 6) * scale)
    border_type = block.get("border", "solid")
    border_width = int(block.get("border_width", 1))
    border_color_name = block.get("border_color", "black")
    border_color = ctx.color_index(border_color_name, default=EINK_FG)

    card_x = ctx.x_offset + margin_x
    card_w = ctx.available_width - margin_x * 2
    inner_w = card_w - padding * 2

    start_y = ctx.y
    inner_h = measure_column_blocks_height(ctx, children, x_offset=card_x + padding, available_width=inner_w)
    card_h = inner_h + padding * 2
    max_card_h = max(20, ctx.footer_top - start_y - 4)
    if card_h > max_card_h:
        card_h = max_card_h
    if border_type == "solid":
        ctx.draw.rounded_rectangle([card_x, start_y, card_x + card_w, start_y + card_h], radius=radius, outline=border_color, width=border_width)
    elif border_type == "dashed":
        draw_dashed_line(ctx.draw, (card_x + radius, start_y), (card_x + card_w - radius, start_y), fill=border_color, width=border_width)
        draw_dashed_line(ctx.draw, (card_x + radius, start_y + card_h), (card_x + card_w - radius, start_y + card_h), fill=border_color, width=border_width)
        draw_dashed_line(ctx.draw, (card_x, start_y + radius), (card_x, start_y + card_h - radius), fill=border_color, width=border_width)
        draw_dashed_line(ctx.draw, (card_x + card_w, start_y + radius), (card_x + card_w, start_y + card_h - radius), fill=border_color, width=border_width)

    child_ctx = RenderContext(
        draw=ctx.draw, img=ctx.img, content=ctx.content,
        screen_w=ctx.screen_w, screen_h=ctx.screen_h,
        y=start_y + padding, x_offset=card_x + padding,
        available_width=inner_w, colors=ctx.colors,
        footer_height=ctx.footer_height, footer_top_offset=ctx.footer_top_offset,
    )
    for child in children:
        if child_ctx.y >= ctx.footer_top - 6:
            break
        render_block(child_ctx, child)

    ctx.y = start_y + card_h + margin_bottom


# 注册所有布局类组件
register_block("separator", render_separator)
register_block("section", render_section)
register_block("vertical_stack", render_vertical_stack)
register_block("conditional", render_conditional)
register_block("spacer", render_spacer)
register_block("two_column", render_two_column)
register_block("group", render_group)
register_block("flex_row", render_flex_row)
register_block("card", render_card)
