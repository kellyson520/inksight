"""
现代视觉与复合交互组件模块 (Modern Visual & Interaction Components)
包含：badge, badge_group, metric_card, segmented_row, striped_table, progress_bar, rating_choices, image
"""
from __future__ import annotations

import logging
from io import BytesIO
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx
from PIL import Image, UnidentifiedImageError

from core.image_processing import convert_image_block
from core.patterns.utils import (
    EINK_BG,
    EINK_FG,
    draw_dashed_line,
    has_cjk,
    load_font,
)
from .context import RenderContext
from .registry import register_block, render_block
from .text import pick_cjk_font

logger = logging.getLogger(__name__)

_BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
_UPLOAD_DIR = _BACKEND_ROOT / "runtime_uploads"


def _num(v: Any) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def render_badge(ctx: RenderContext, block: dict) -> None:
    field_name = block.get("field")
    template = block.get("template")
    if field_name:
        text = str(ctx.get_field(field_name))
    elif template:
        text = ctx.resolve(template)
    else:
        text = str(block.get("text", ""))

    if not text:
        return

    font_size = int(block.get("font_size", 12) * ctx.scale)
    font_key = block.get("font", "noto_serif_bold")
    if has_cjk(text):
        font_key = pick_cjk_font(font_key)
    font = load_font(font_key, font_size)

    bbox = font.getbbox(text)
    tw = bbox[2] - bbox[0]
    th = max(bbox[3], font_size)

    pad_x = int(block.get("padding_x", 8) * ctx.scale)
    pad_y = int(block.get("padding_y", 3) * ctx.scale)
    badge_w = tw + pad_x * 2
    badge_h = th + pad_y * 2
    radius = int(block.get("radius", badge_h // 2) * ctx.scale)
    if "radius" not in block:
        radius = badge_h // 2

    align = block.get("align", "center")
    margin_x = int(block.get("margin_x", 0) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 6) * ctx.scale)

    if align == "center":
        bx = ctx.x_offset + (ctx.available_width - badge_w) // 2
    elif align == "right":
        bx = ctx.x_offset + ctx.available_width - badge_w - margin_x
    else:
        bx = ctx.x_offset + margin_x

    by = ctx.y
    variant = block.get("variant", "solid")
    bg_color_name = block.get("bg_color", "red" if ctx.colors >= 3 else "black")
    text_color_name = block.get("color")
    bg_fill = ctx.color_index(bg_color_name, default=EINK_FG)

    if variant == "solid":
        ctx.draw.rounded_rectangle([bx, by, bx + badge_w, by + badge_h], radius=radius, fill=bg_fill)
        text_fill = ctx.color_index(text_color_name, default=EINK_BG) if text_color_name else EINK_BG
    elif variant == "outline":
        ctx.draw.rounded_rectangle([bx, by, bx + badge_w, by + badge_h], radius=radius, outline=bg_fill, width=1)
        text_fill = ctx.color_index(text_color_name, default=bg_fill) if text_color_name else bg_fill
    else:
        text_fill = ctx.color_index(text_color_name, default=EINK_FG)

    tx = bx + pad_x - bbox[0]
    ty = by + pad_y + max(0, (badge_h - 2 * pad_y - (bbox[3] - bbox[1])) // 2) - bbox[1]
    ctx.draw.text((tx, ty), text, fill=text_fill, font=font)
    ctx.y += badge_h + margin_bottom


def render_badge_group(ctx: RenderContext, block: dict) -> None:
    badges = block.get("badges", [])
    if not badges:
        return
    flex_data = {
        "type": "flex_row",
        "justify": block.get("justify", "center"),
        "align_items": "center",
        "gap": block.get("gap", 6),
        "margin_x": block.get("margin_x", 0),
        "margin_bottom": block.get("margin_bottom", 6),
        "items": badges,
    }
    render_block(ctx, flex_data)


def render_metric_card(ctx: RenderContext, block: dict) -> None:
    scale = ctx.scale
    margin_x = int(block.get("margin_x", 12) * scale)
    margin_bottom = int(block.get("margin_bottom", 8) * scale)
    padding = int(block.get("padding", 10) * scale)
    radius = int(block.get("radius", 6) * scale)
    card_w = ctx.available_width - margin_x * 2
    card_x = ctx.x_offset + margin_x
    start_y = ctx.y

    title = ctx.resolve(str(ctx.get_field(block.get("title_field", "")) if block.get("title_field") else block.get("title", "")))
    val = ctx.resolve(str(ctx.get_field(block.get("field", "")) if block.get("field") else block.get("value", "")))
    unit = ctx.resolve(str(block.get("unit", "")))
    badge_text = ctx.resolve(str(ctx.get_field(block.get("badge_field", "")) if block.get("badge_field") else block.get("badge", "")))
    sub = ctx.resolve(str(ctx.get_field(block.get("sub_field", "")) if block.get("sub_field") else block.get("subtitle", "")))

    font_title = load_font("noto_serif_regular", int(12 * scale))
    font_val = load_font("noto_serif_bold", int(block.get("font_size", 28) * scale))
    font_unit = load_font("noto_serif_light", int(12 * scale))
    font_sub = load_font("noto_serif_light", int(11 * scale))

    v_bbox = font_val.getbbox(val) if val else (0, 0, 0, 0)
    card_h = padding * 2 + int(14 * scale) + (v_bbox[3] - v_bbox[1]) + (int(14 * scale) if sub else 0) + 6

    border_type = block.get("border", "solid")
    if border_type == "solid":
        ctx.draw.rounded_rectangle([card_x, start_y, card_x + card_w, start_y + card_h], radius=radius, outline=EINK_FG, width=1)
    elif border_type == "dashed":
        draw_dashed_line(ctx.draw, (card_x, start_y), (card_x + card_w, start_y), fill=EINK_FG)
        draw_dashed_line(ctx.draw, (card_x, start_y + card_h), (card_x + card_w, start_y + card_h), fill=EINK_FG)
        draw_dashed_line(ctx.draw, (card_x, start_y), (card_x, start_y + card_h), fill=EINK_FG)
        draw_dashed_line(ctx.draw, (card_x + card_w, start_y), (card_x + card_w, start_y + card_h), fill=EINK_FG)

    cur_y = start_y + padding
    if title:
        ctx.draw.text((card_x + padding, cur_y), title, fill=EINK_FG, font=font_title)
    if badge_text:
        badge_font = load_font("noto_serif_bold", int(10 * scale))
        bb = badge_font.getbbox(badge_text)
        bw = bb[2] - bb[0] + 10
        bh = max(bb[3], int(10 * scale)) + 4
        bx = card_x + card_w - padding - bw
        ctx.draw.rounded_rectangle([bx, cur_y - 1, bx + bw, cur_y + bh - 1], radius=4, fill=ctx.color_index(block.get("badge_color", "red"), default=EINK_FG))
        ctx.draw.text((bx + 5 - bb[0], cur_y + 1 - bb[1]), badge_text, fill=EINK_BG, font=badge_font)

    cur_y += int(16 * scale)
    val_color = ctx.color_index(block.get("color", "black"), default=EINK_FG)
    ctx.draw.text((card_x + padding - v_bbox[0], cur_y - v_bbox[1]), val, fill=val_color, font=font_val)
    if unit:
        vw = v_bbox[2] - v_bbox[0]
        ctx.draw.text((card_x + padding + vw + 4, cur_y + (v_bbox[3] - v_bbox[1]) - int(14 * scale)), unit, fill=EINK_FG, font=font_unit)

    cur_y += (v_bbox[3] - v_bbox[1]) + 4
    if sub:
        ctx.draw.text((card_x + padding, cur_y), sub, fill=EINK_FG, font=font_sub)

    ctx.y = start_y + card_h + margin_bottom


def render_striped_table(ctx: RenderContext, block: dict) -> None:
    columns = block.get("columns", [])
    rows = block.get("rows", [])
    if not columns or not rows:
        return

    scale = ctx.scale
    margin_x = int(block.get("margin_x", 12) * scale)
    margin_bottom = int(block.get("margin_bottom", 8) * scale)
    table_w = ctx.available_width - margin_x * 2
    start_x = ctx.x_offset + margin_x
    start_y = ctx.y

    col_count = len(columns)
    col_w = table_w // col_count
    font_hdr = load_font("noto_serif_bold", int(11 * scale))
    font_row = load_font("noto_serif_regular", int(12 * scale))

    cur_y = start_y
    for i, col in enumerate(columns):
        cx = start_x + i * col_w
        lbl = col.get("label", "")
        ctx.draw.text((cx + 4, cur_y), lbl, fill=EINK_FG, font=font_hdr)
    cur_y += int(16 * scale)
    ctx.draw.line([(start_x, cur_y), (start_x + table_w, cur_y)], fill=EINK_FG, width=1)
    cur_y += 3

    row_h = int(block.get("row_height", 18) * scale)
    for r_idx, row_data in enumerate(rows):
        if cur_y >= ctx.footer_top - 6:
            break
        if r_idx % 2 == 1 and block.get("striped", True):
            for px in range(start_x, start_x + table_w):
                if px % 2 == 0:
                    for py in range(cur_y, cur_y + row_h - 1):
                        if (px + py) % 4 == 0:
                            ctx.draw.point((px, py), fill=EINK_FG)

        for c_idx, col in enumerate(columns):
            cx = start_x + c_idx * col_w
            key = col.get("key")
            val = str(row_data.get(key, "") if isinstance(row_data, dict) else (row_data[c_idx] if c_idx < len(row_data) else ""))
            ctx.draw.text((cx + 4, cur_y + 2), val, fill=EINK_FG, font=font_row)
        cur_y += row_h

    ctx.y = cur_y + margin_bottom


def render_segmented_row(ctx: RenderContext, block: dict) -> None:
    scale = ctx.scale
    segments = max(1, int(block.get("segments", 5)))
    active = int(ctx.get_field(block.get("active_field", "")) if block.get("active_field") else block.get("active", 3))
    margin_x = int(block.get("margin_x", 16) * scale)
    margin_bottom = int(block.get("margin_bottom", 6) * scale)
    h = int(block.get("height", 6) * scale)
    gap = int(block.get("gap", 4) * scale)
    radius = int(block.get("radius", 2) * scale)

    total_w = ctx.available_width - margin_x * 2
    seg_w = (total_w - (segments - 1) * gap) // segments
    start_x = ctx.x_offset + margin_x
    start_y = ctx.y

    active_fill = ctx.color_index(block.get("active_color", "red" if ctx.colors >= 3 else "black"), default=EINK_FG)

    for i in range(segments):
        sx = start_x + i * (seg_w + gap)
        if i < active:
            ctx.draw.rounded_rectangle([sx, start_y, sx + seg_w, start_y + h], radius=radius, fill=active_fill)
        else:
            ctx.draw.rounded_rectangle([sx, start_y, sx + seg_w, start_y + h], radius=radius, outline=EINK_FG, width=1)

    ctx.y = start_y + h + margin_bottom


def render_progress_bar(ctx: RenderContext, block: dict) -> None:
    value = _num(ctx.get_field(block.get("field", "")))
    max_value = max(_num(ctx.get_field(block.get("max_field", ""))), 1)
    ratio = max(0.0, min(1.0, value / max_value))
    width = int(block.get("width", 80) * ctx.scale)
    height = int(block.get("height", 6) * ctx.scale)
    _raw_margin = block.get("margin_x")
    if _raw_margin is not None:
        margin_x = int(_raw_margin * ctx.scale)
    else:
        margin_x = int(ctx.screen_w * 0.06)
    x = ctx.x_offset + margin_x
    y = ctx.y
    ctx.draw.rectangle([x, y, x + width, y + height], outline=EINK_FG, width=1)
    fill_w = int((width - 2) * ratio)
    if fill_w > 0:
        ctx.draw.rectangle([x + 1, y + 1, x + 1 + fill_w, y + height - 1], fill=EINK_FG)
    ctx.y += height + 6


def render_rating_choices(ctx: RenderContext, block: dict) -> None:
    labels = block.get("labels") or ["忘了", "模糊", "记住"]
    if not isinstance(labels, list) or not labels:
        return

    try:
        selected = int(ctx.get_field(block.get("selected_field", "rating_cursor")) or 0)
    except (TypeError, ValueError):
        selected = 0
    selected %= len(labels)

    font_size = int(block.get("font_size", 14) * ctx.scale)
    font_key = block.get("font", "noto_serif_regular")
    if any(has_cjk(str(label)) for label in labels):
        font_key = pick_cjk_font(font_key)
    font = load_font(font_key, font_size)

    _raw_margin = block.get("margin_x")
    if _raw_margin is not None:
        margin_x = int(_raw_margin * ctx.scale)
    else:
        margin_x = int(ctx.screen_w * 0.06)

    total_w = ctx.available_width - margin_x * 2
    item_w = total_w // len(labels)
    h = font_size + int(10 * ctx.scale)

    for i, label in enumerate(labels):
        x = ctx.x_offset + margin_x + i * item_w
        if i == selected:
            ctx.draw.rounded_rectangle([x + 2, ctx.y, x + item_w - 2, ctx.y + h], radius=4, fill=EINK_FG)
            text_color = EINK_BG
        else:
            ctx.draw.rounded_rectangle([x + 2, ctx.y, x + item_w - 2, ctx.y + h], radius=4, outline=EINK_FG, width=1)
            text_color = EINK_FG

        bbox = font.getbbox(str(label))
        tw = bbox[2] - bbox[0]
        tx = x + (item_w - tw) // 2
        ty = ctx.y + (h - (bbox[3] - bbox[1])) // 2 - bbox[1]
        ctx.draw.text((tx, ty), str(label), fill=text_color, font=font)

    ctx.y += h + int(8 * ctx.scale)


def _resolve_local_asset(path: str) -> str | None:
    if not path:
        return None
    if path.startswith("/static/"):
        static_rel = path.lstrip("/")
        backend_static = Path(__file__).resolve().parent.parent.parent / static_rel
        if backend_static.exists() and backend_static.is_file():
            return str(backend_static)
    if path.startswith("/api/uploads/"):
        upload_id = path.rsplit("/", 1)[-1].strip()
        if not upload_id:
            return None
        try:
            __import__("uuid").UUID(upload_id)
        except ValueError:
            return None
        local = _UPLOAD_DIR / f"{upload_id}.bin"
        if local.exists() and local.is_file():
            return str(local)
    return None


def _is_upload_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
    except ValueError:
        return False
    path = parsed.path or url
    return path.startswith("/api/uploads/")


def _draw_image_placeholder(ctx: RenderContext, x: int, y: int, width: int, height: int, text: str) -> None:
    ctx.draw.rectangle([x, y, x + width, y + height], outline=EINK_FG, width=1)
    placeholder_font = load_font("noto_serif_light", int(12 * ctx.scale))
    bbox = placeholder_font.getbbox(text)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    tx = x + (width - tw) // 2
    ty = y + (height - th) // 2
    ctx.draw.text((tx, ty), text, fill=EINK_FG, font=placeholder_font)


def render_image(ctx: RenderContext, block: dict) -> None:
    field_name = block.get("field", "image_url")
    image_url = str(ctx.get_field(field_name) or "")
    if not image_url:
        return
    width = int(block.get("width", 220) * ctx.scale)
    height = int(block.get("height", 140) * ctx.scale)
    default_x = ctx.x_offset + max(0, (ctx.available_width - width) // 2)
    x = int(block.get("x", default_x))
    y = int(block.get("y", ctx.y))
    fit = str(block.get("fit", "fill") or "fill")
    align_x = str(block.get("align_x", "center") or "center")
    align_y = str(block.get("align_y", "center") or "center")
    photo_enhance = bool(block.get("photo_enhance", False))
    margin_bottom = int(block.get("margin_bottom", 6) * ctx.scale)

    prefetched = ctx.content.get(f"_prefetched_{field_name}")
    if prefetched:
        img = convert_image_block(
            Image.open(BytesIO(prefetched)),
            width, height, ctx.colors,
            fit=fit, align_x=align_x, align_y=align_y,
            photo_enhance=photo_enhance,
        )
        if ctx.colors >= 3:
            ctx.img.paste(img, (x, y))
        else:
            ctx.paste_icon(img, (x, y))
        ctx.y = y + height + margin_bottom
        return

    local_path = _resolve_local_asset(image_url)
    if local_path:
        try:
            img = convert_image_block(
                Image.open(local_path),
                width, height, ctx.colors,
                fit=fit, align_x=align_x, align_y=align_y,
                photo_enhance=photo_enhance,
            )
            if ctx.colors >= 3:
                ctx.img.paste(img, (x, y))
            else:
                ctx.paste_icon(img, (x, y))
            ctx.y = y + height + margin_bottom
            return
        except (OSError, UnidentifiedImageError):
            logger.warning("[JSONRenderer] Failed to load local asset %s", local_path, exc_info=True)
    elif _is_upload_url(image_url):
        logger.warning("[JSONRenderer] Uploaded image link expired: %s", image_url)
        _draw_image_placeholder(ctx, x, y, width, height, "Image link expired")
        ctx.y = y + height + margin_bottom
        return

    try:
        resp = None
        last_error = None
        attempts = [
            {"trust_env": True, "timeout": httpx.Timeout(connect=8.0, read=12.0, write=8.0, pool=8.0)},
            {"trust_env": False, "timeout": httpx.Timeout(connect=12.0, read=18.0, write=10.0, pool=10.0)},
        ]
        req_referer = "https://weread.qq.com/"
        if "douban" in image_url:
            req_referer = "https://movie.douban.com/"
        elif "smzdm" in image_url:
            req_referer = "https://www.smzdm.com/"

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": req_referer,
        }
        for opts in attempts:
            try:
                with httpx.Client(timeout=opts["timeout"], follow_redirects=True, trust_env=opts["trust_env"], headers=headers) as client:
                    resp = client.get(image_url)
                if resp.status_code >= 400:
                    raise ValueError(f"HTTP {resp.status_code}")
                break
            except (httpx.HTTPError, ValueError) as e:
                last_error = e
                resp = None
        if resp is None:
            raise last_error if last_error else ValueError("image fetch failed")

        img = convert_image_block(
            Image.open(BytesIO(resp.content)),
            width, height, ctx.colors,
            fit=fit, align_x=align_x, align_y=align_y,
            photo_enhance=photo_enhance,
        )
        if ctx.colors >= 3:
            ctx.img.paste(img, (x, y))
        else:
            ctx.paste_icon(img, (x, y))
        ctx.y = y + height + margin_bottom
    except Exception as exc:
        logger.warning("[JSONRenderer] Image block download failed: %s", exc)
        _draw_image_placeholder(ctx, x, y, width, height, "Image not available")
        ctx.y = y + height + margin_bottom


# 注册所有组件类组件
register_block("badge", render_badge)
register_block("badge_group", render_badge_group)
register_block("metric_card", render_metric_card)
register_block("segmented_row", render_segmented_row)
register_block("striped_table", render_striped_table)
register_block("progress_bar", render_progress_bar)
register_block("rating_choices", render_rating_choices)
register_block("image", render_image)
