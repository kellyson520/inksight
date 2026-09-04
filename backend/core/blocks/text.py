"""
文本与基础信息排版组件模块 (Text & Basic Typography Blocks)
包含：centered_text, text, list, icon_text, weather_icon_text, big_number, icon_list, key_value, weather_icon
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
    wrap_text,
)
from .context import RenderContext, section_icon_from_label
from .registry import register_block

logger = logging.getLogger(__name__)


def pick_cjk_font(font_key: str) -> str:
    """确保中文字符串选用兼容的 Noto Serif 字体变体。"""
    if font_key.startswith("noto_serif"):
        return font_key
    if font_key in ("lora_regular", "lora_bold", "inter_medium"):
        return "noto_serif_light"
    return font_key


def render_centered_text(ctx: RenderContext, block: dict, *, use_full_body: bool = False) -> None:
    field_name = block.get("field", "text")
    text = str(ctx.get_field(field_name))
    if not text:
        return

    font_size = max(10, int(block.get("font_size", 16) * ctx.scale))
    font_name = block.get("font_name")
    font_key = block.get("font", "noto_serif_light")
    max_ratio = block.get("max_width_ratio", 0.88)
    line_spacing = int(block.get("line_spacing", 8) * ctx.scale)

    body_height = ctx.footer_top - ctx.y
    max_w = int(ctx.available_width * max_ratio)
    lines = []
    font = None
    line_h = font_size + line_spacing
    total_h = 0
    while font_size >= 10:
        if font_name:
            if has_cjk(text) and "Noto" not in font_name:
                font_name = "NotoSerifSC-Light.ttf"
            font = load_font_by_name(font_name, font_size)
        else:
            if has_cjk(text):
                font_key = "noto_serif_light"
            font = load_font(font_key, font_size)

        lines = wrap_text(text, font, max_w)
        line_h = font_size + line_spacing
        total_h = len(lines) * line_h

        if use_full_body and block.get("vertical_center", True) and total_h > body_height:
            font_size -= 2
        else:
            break

    if use_full_body and block.get("vertical_center", True):
        y_start = ctx.y + (body_height - total_h) // 2
    else:
        y_start = ctx.y

    for i, line in enumerate(lines):
        bbox = font.getbbox(line)
        lw = bbox[2] - bbox[0]
        x = ctx.x_offset + (ctx.available_width - lw) // 2
        ctx.draw.text((x, y_start + i * line_h), line, fill=ctx.resolve_color(block), font=font)

    ctx.y = y_start + total_h + 4


def render_text(ctx: RenderContext, block: dict) -> None:
    template = block.get("template", "")
    field_name = block.get("field")
    if field_name:
        text = str(ctx.get_field(field_name))
    elif template:
        text = ctx.resolve(template)
    else:
        return

    if not text:
        return

    font_size = int(block.get("font_size", 14) * ctx.scale)
    font_name = block.get("font_name")
    font_key = block.get("font", "noto_serif_regular")
    if font_name and not has_cjk(text):
        font = load_font_by_name(font_name, font_size)
    elif has_cjk(text):
        font_key = pick_cjk_font(font_key)
        font = load_font(font_key, font_size)
    else:
        font = load_font(font_key, font_size)

    align = block.get("align", "center")
    margin_x = block.get("margin_x")
    if margin_x is not None:
        margin_x = int(margin_x * ctx.scale)
    else:
        margin_x = int(ctx.screen_w * 0.06)
    max_lines = block.get("max_lines", 3)
    max_w = max(20, ctx.available_width - margin_x * 2)
    line_height = block.get("line_height")
    if line_height is not None:
        line_height = int(line_height * ctx.scale)
    else:
        line_height = font_size + 6

    lines = wrap_text(text, font, max_w)

    if max_lines and len(lines) > max_lines:
        lines = lines[:max_lines]
        if lines and block.get("ellipsis", True):
            lines[-1] = lines[-1].rstrip() + "..."

    start_y = ctx.y
    rendered_lines = 0
    last_line_bottom = font_size
    for line in lines:
        line_y = start_y + rendered_lines * line_height
        if line_y >= ctx.footer_top - 10:
            break
        bbox = font.getbbox(line)
        lw = bbox[2] - bbox[0]
        last_line_bottom = max(1, bbox[3])
        if align == "center":
            x = ctx.x_offset + (ctx.available_width - lw) // 2
        elif align == "right":
            x = ctx.x_offset + ctx.available_width - margin_x - lw
        else:
            x = ctx.x_offset + margin_x
        ctx.draw.text((x, line_y), line, fill=ctx.resolve_color(block), font=font)
        rendered_lines += 1
    if rendered_lines:
        used_h = max(rendered_lines * line_height, (rendered_lines - 1) * line_height + last_line_bottom)
        min_height = block.get("min_height")
        if min_height is not None:
            used_h = max(used_h, int(min_height * ctx.scale))
        ctx.y = start_y + used_h
        margin_bottom = block.get("margin_bottom")
        if margin_bottom is not None:
            ctx.y += int(margin_bottom * ctx.scale)


def render_list(ctx: RenderContext, block: dict) -> None:
    field_name = block.get("field", "items")
    items = ctx.get_field(field_name)
    if not isinstance(items, list) or not items:
        return

    font_key = block.get("font", "noto_serif_regular")
    font_size = int(block.get("font_size", 13) * ctx.scale)
    spacing = int(block.get("spacing", font_size + 6) * ctx.scale)
    numbered = block.get("numbered", False)
    template = block.get("item_template", "")
    align = block.get("align", "left")
    margin_x = block.get("margin_x")
    if margin_x is not None:
        margin_x = int(margin_x * ctx.scale)
    else:
        margin_x = int(ctx.available_width * 0.06)
    right_field = block.get("right_field")

    max_items = block.get("max_items", 5)
    rendered_count = 0
    last_item_spacing = spacing
    last_item_last_line_h = font_size

    for i, item in enumerate(items[:max_items]):
        font = load_font(pick_cjk_font(font_key), font_size)
        if isinstance(item, dict):
            text = template
            for k, v in item.items():
                text = text.replace(f"{{{k}}}", str(v))
            if not template:
                text = str(item.get("title") or item.get("text") or item.get("name") or "")
        else:
            text = str(item)
            if template and "{_value}" in template:
                text = template.replace("{_value}", str(item))

        if numbered:
            text = f"{i + 1}. {text}"
        text = text.replace("{index}", str(i + 1))

        right_col_w = int(80 * ctx.scale)
        max_text_w = ctx.available_width - margin_x * 2 if not right_field else ctx.available_width - margin_x - right_col_w
        lines = wrap_text(text, font, max_text_w)
        item_height = spacing * max(1, len(lines))

        if ctx.y + item_height > ctx.footer_top:
            remaining = len(items) - rendered_count
            if remaining > 0:
                more_text = f"+{remaining} more"
                more_font = load_font(pick_cjk_font(font_key), int(11 * ctx.scale))
                ctx.draw.text((ctx.x_offset + margin_x, ctx.y), more_text, fill=ctx.resolve_color(block), font=more_font)
            break
        if ctx.y >= ctx.footer_top - 10:
            break

        color = ctx.resolve_color(block)
        last_line_h = font_size
        if align == "center":
            for line_idx, ln in enumerate(lines):
                bbox = font.getbbox(ln)
                lw = bbox[2] - bbox[0]
                last_line_h = max(1, bbox[3] - bbox[1])
                ctx.draw.text((ctx.x_offset + (ctx.available_width - lw) // 2, ctx.y + line_idx * spacing), ln, fill=color, font=font)
        else:
            for line_idx, ln in enumerate(lines):
                bbox = font.getbbox(ln)
                last_line_h = max(1, bbox[3] - bbox[1])
                ctx.draw.text((ctx.x_offset + margin_x, ctx.y + line_idx * spacing), ln, fill=color, font=font)

        if right_field and isinstance(item, dict):
            rv = str(item.get(right_field, ""))
            if rv:
                score_y = ctx.y + (max(1, len(lines)) - 1) * spacing
                score_bbox = font.getbbox(rv)
                score_w = score_bbox[2] - score_bbox[0]
                score_x = ctx.x_offset + ctx.available_width - margin_x - score_w
                ctx.draw.text((score_x, score_y), rv, fill=color, font=font)

        ctx.y += item_height
        rendered_count += 1
        last_item_spacing = spacing
        last_item_last_line_h = last_line_h
    if rendered_count:
        ctx.y = ctx.y - last_item_spacing + last_item_last_line_h


def render_icon_text(ctx: RenderContext, block: dict) -> None:
    icon_name = block.get("icon")
    field_name = block.get("field")
    text = str(ctx.get_field(field_name)) if field_name else block.get("text", "")
    text = ctx.resolve(text)
    if not text:
        return

    font_key = block.get("font", "noto_serif_regular")
    font_size = int(block.get("font_size", 14) * ctx.scale)
    icon_size = int(block.get("icon_size", 12) * ctx.scale)
    margin_x = block.get("margin_x")
    if margin_x is not None:
        margin_x = int(margin_x * ctx.scale)
    else:
        margin_x = int(ctx.screen_w * 0.06)

    if has_cjk(text):
        font_key = pick_cjk_font(font_key)
    font = load_font(font_key, font_size)

    x = ctx.x_offset + margin_x
    if icon_name:
        icon_img = load_icon(icon_name, size=(icon_size, icon_size))
        if icon_img:
            ctx.paste_icon(icon_img, (x, ctx.y))
            x += icon_size + 4

    ctx.draw.text((x, ctx.y), text, fill=ctx.resolve_color(block), font=font)
    ctx.y += font_size + 6


def render_weather_icon_text(ctx: RenderContext, block: dict) -> None:
    from core.patterns.utils import get_weather_icon

    code_field = block.get("code_field", "today_code")
    text_field = block.get("field")
    template = block.get("text", "")

    code_val = ctx.get_field(code_field)
    try:
        if isinstance(code_val, str):
            code_int = int(code_val)
        else:
            code_int = int(code_val)
    except (TypeError, ValueError):
        code_int = -1

    if text_field:
        text = str(ctx.get_field(text_field))
    else:
        text = template or ""
        text = ctx.resolve(text)

    if not text:
        return

    font_key = block.get("font", "noto_serif_regular")
    font_size = int(block.get("font_size", 14) * ctx.scale)
    icon_size = int(block.get("icon_size", 18) * ctx.scale)
    icon_gap = int(block.get("icon_gap", 4) * ctx.scale)
    margin_x = block.get("margin_x")
    if margin_x is not None:
        margin_x = int(margin_x * ctx.scale)
    else:
        margin_x = int(ctx.screen_w * 0.06)
    align = str(block.get("align", "left") or "left")
    margin_bottom = int(block.get("margin_bottom", 6) * ctx.scale)
    icon_y_offset = int(block.get("icon_y_offset", 0) * ctx.scale)

    suffix_field = block.get("suffix_field")
    suffix_template = block.get("suffix_text", "")
    if suffix_field:
        suffix_text = str(ctx.get_field(suffix_field))
    else:
        suffix_text = ctx.resolve(suffix_template) if suffix_template else ""

    suffix_font_key = block.get("suffix_font", font_key)
    suffix_font_size = int(block.get("suffix_font_size", font_size) * ctx.scale)
    suffix_gap = int(block.get("suffix_gap", 6) * ctx.scale)

    font = load_font(pick_cjk_font(font_key) if has_cjk(text) else font_key, font_size)
    text_bbox = font.getbbox(text)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = max(font_size, text_bbox[3] - text_bbox[1])

    icon_img = None
    if code_int >= 0:
        icon_img = get_weather_icon(code_int, size=(icon_size, icon_size))

    icon_w = icon_size if icon_img else 0
    actual_gap = icon_gap if icon_img else 0

    suffix_font = None
    suffix_width = 0
    suffix_height = 0
    if suffix_text:
        suffix_font = load_font(pick_cjk_font(suffix_font_key) if has_cjk(suffix_text) else suffix_font_key, suffix_font_size)
        s_bbox = suffix_font.getbbox(suffix_text)
        suffix_width = s_bbox[2] - s_bbox[0]
        suffix_height = max(suffix_font_size, s_bbox[3] - s_bbox[1])
        actual_suffix_gap = suffix_gap
    else:
        actual_suffix_gap = 0

    total_w = icon_w + actual_gap + text_width + actual_suffix_gap + suffix_width

    if align == "center":
        start_x = ctx.x_offset + (ctx.available_width - total_w) // 2
    elif align == "right":
        start_x = ctx.x_offset + ctx.available_width - margin_x - total_w
    else:
        start_x = ctx.x_offset + margin_x

    curr_x = start_x
    if icon_img:
        ctx.paste_icon(icon_img, (curr_x, ctx.y + icon_y_offset))
        curr_x += icon_w + actual_gap

    text_y_offset = int(block.get("text_y_offset", 0) * ctx.scale)
    ctx.draw.text((curr_x, ctx.y + text_y_offset), text, fill=ctx.resolve_color(block), font=font)
    curr_x += text_width

    if suffix_text and suffix_font:
        curr_x += actual_suffix_gap
        suffix_color = ctx.color_index(block.get("suffix_color", "black"), default=EINK_FG)
        ctx.draw.text((curr_x, ctx.y + text_y_offset), suffix_text, fill=suffix_color, font=suffix_font)

    row_h = max(icon_size, text_height, suffix_height)
    ctx.y += row_h + margin_bottom


def render_big_number(ctx: RenderContext, block: dict) -> None:
    field_name = block.get("field", "")
    text = str(ctx.get_field(field_name))
    if not text or text == "--":
        return

    unit = block.get("unit", "")
    if unit:
        text = f"{text}{unit}"

    font_size = int(block.get("font_size", 42) * ctx.scale)
    font_key = block.get("font", "noto_serif_bold")
    if has_cjk(text):
        font_key = pick_cjk_font(font_key)
    font = load_font(font_key, font_size)
    bbox = font.getbbox(text)
    tw = bbox[2] - bbox[0]
    align = block.get("align", "center")
    _raw_margin = block.get("margin_x")
    if _raw_margin is not None:
        margin_x = int(_raw_margin * ctx.scale)
    else:
        margin_x = int(ctx.available_width * 0.06)
    if align == "left":
        x = ctx.x_offset + margin_x - bbox[0]
    elif align == "right":
        x = ctx.x_offset + ctx.available_width - margin_x - tw - bbox[0]
    else:
        x = ctx.x_offset + (ctx.available_width - tw) // 2 - bbox[0]
    y = ctx.y - bbox[1]
    ctx.draw.text((x, y), text, fill=ctx.resolve_color(block), font=font)
    ctx.y += max(0, bbox[3] - bbox[1]) + 6


def render_key_value(ctx: RenderContext, block: dict) -> None:
    label = block.get("label", "")
    field_name = block.get("field", "")
    val = ctx.get_field(field_name) if field_name else block.get("value", "")
    if isinstance(val, dict):
        val = " \u00b7 ".join(f"{k}: {v}" for k, v in val.items())
    elif isinstance(val, list):
        val = ", ".join(str(x) for x in val)
    else:
        val = str(val)
    if not val:
        return

    font_size = int(block.get("font_size", 12) * ctx.scale)
    lbl_font = load_font("noto_serif_light", font_size)
    val_font = load_font("noto_serif_regular", font_size)
    margin_x = block.get("margin_x")
    if margin_x is not None:
        margin_x = int(margin_x * ctx.scale)
    else:
        margin_x = int(ctx.screen_w * 0.06)
    x = ctx.x_offset + margin_x

    if label:
        ctx.draw.text((x, ctx.y), f"{label}: ", fill=EINK_FG, font=lbl_font)
        lbl_bbox = lbl_font.getbbox(f"{label}: ")
        x += lbl_bbox[2] - lbl_bbox[0]

    ctx.draw.text((x, ctx.y), val, fill=ctx.resolve_color(block), font=val_font)
    ctx.y += font_size + 6


def render_icon_list(ctx: RenderContext, block: dict) -> None:
    items = block.get("items", [])
    if not items:
        field_name = block.get("field")
        if field_name:
            items = ctx.get_field(field_name) or []
    if not isinstance(items, list) or not items:
        return

    icon_size = int(block.get("icon_size", 14) * ctx.scale)
    font_size = int(block.get("font_size", 12) * ctx.scale)
    margin_x = int(block.get("margin_x", 12) * ctx.scale)
    item_gap = int(block.get("item_gap", 8) * ctx.scale)
    font = load_font("noto_serif_regular", font_size)

    for item in items:
        if not isinstance(item, dict):
            continue
        ic = item.get("icon")
        txt = ctx.resolve(item.get("text", ""))
        cur_x = ctx.x_offset + margin_x
        if ic:
            img = load_icon(ic, size=(icon_size, icon_size))
            if img:
                ctx.paste_icon(img, (cur_x, ctx.y))
                cur_x += icon_size + 4
        if txt:
            ctx.draw.text((cur_x, ctx.y), txt, fill=EINK_FG, font=font)
        ctx.y += max(icon_size, font_size) + item_gap


def render_weather_icon(ctx: RenderContext, block: dict) -> None:
    from core.patterns.utils import get_weather_icon

    field_name = block.get("field", "code")
    weather_code = ctx.get_field(field_name)
    try:
        if isinstance(weather_code, str):
            weather_code = int(weather_code)
        elif not isinstance(weather_code, int):
            weather_code = -1
    except (ValueError, TypeError):
        weather_code = -1

    if weather_code < 0:
        return

    icon_size = int(block.get("size", 24) * ctx.scale)
    icon_img = get_weather_icon(weather_code, size=(icon_size, icon_size))
    if not icon_img:
        return

    align = block.get("align", "center")
    margin_x = block.get("margin_x")
    if margin_x is not None:
        margin_x = int(margin_x * ctx.scale)
    else:
        margin_x = int(ctx.screen_w * 0.06)

    if align == "center":
        x = ctx.x_offset + (ctx.available_width - icon_size) // 2
    elif align == "right":
        x = ctx.x_offset + ctx.available_width - margin_x - icon_size
    else:
        x = ctx.x_offset + margin_x

    ctx.paste_icon(icon_img, (x, ctx.y))
    margin_bottom = block.get("margin_bottom")
    if margin_bottom is not None:
        ctx.y += icon_size + int(margin_bottom * ctx.scale)
    else:
        ctx.y += icon_size + 4


# 注册所有文本类组件
register_block("centered_text", render_centered_text)
register_block("text", render_text)
register_block("list", render_list)
register_block("icon_text", render_icon_text)
register_block("weather_icon_text", render_weather_icon_text)
register_block("big_number", render_big_number)
register_block("key_value", render_key_value)
register_block("icon_list", render_icon_list)
register_block("weather_icon", render_weather_icon)
