"""Compact recommendation list/card renderer for external media modes."""
from __future__ import annotations
from PIL import ImageDraw
from .context import RenderContext
from .registry import register_block
from .text import pick_cjk_font
from .components import render_image
from ..patterns.utils import load_font, EINK_FG


@register_block("recommendation")
def render_recommendation(ctx: RenderContext, block: dict) -> None:
    items = ctx.get_field(block.get("field", "items"))
    if not isinstance(items, list): return
    style = str(ctx.get_field(block.get("style_field", "layout_style")) or "ranking")
    max_items = int(block.get("max_items", 5))
    font_size = int(block.get("font_size", 10) * ctx.scale)
    font = load_font("noto_serif_regular", font_size)
    bold = load_font("noto_serif_bold", font_size)
    y = ctx.y
    for index, item in enumerate(items[:max_items], 1):
        if not isinstance(item, dict): continue
        title = str(item.get("title", "推荐")).strip()
        subtitle = str(item.get("subtitle", "")).strip()
        rank = str(item.get("rank_label") or f"NO.{index}")
        if style == "cover_card":
            image_data = item.get("image_data")
            image_url = str(item.get("thumbnail_url") or item.get("cover_url") or "").strip()
            # If card_height isn't explicitly configured large in the block, calculate available vertical space
            default_h = max(font_size + int(8 * ctx.scale), int(block.get("card_height", 0) * ctx.scale))
            if default_h <= 0:
                remaining_h = ctx.screen_h - ctx.footer_height - y - int(10 * ctx.scale)
                card_height = max(100, remaining_h)
            else:
                card_height = default_h
            if image_data is not None or image_url:
                previous_image = ctx.content.get("__recommendation_image")
                ctx.content["__recommendation_image"] = image_data if image_data is not None else image_url
                # Draw image
                img_h = max(20, card_height - font_size - int(10 * ctx.scale))
                render_image(ctx, {"field": "__recommendation_image", "width": max(20, ctx.available_width - int(20 * ctx.scale)), "height": img_h, "x": ctx.x_offset + int(10 * ctx.scale), "y": y, "fit": "contain"})
                if previous_image is None:
                    ctx.content.pop("__recommendation_image", None)
                else:
                    ctx.content["__recommendation_image"] = previous_image
            line = f"{rank}  {title}"
            if subtitle: line += f" · {subtitle}"
            ctx.draw.text((ctx.x_offset + int(10 * ctx.scale), y + card_height - font_size - int(2 * ctx.scale)), line[:48], fill=EINK_FG, font=bold)
            y += card_height + int(4 * ctx.scale)
        else:
            line = f"{rank}  {title}"
            if subtitle: line += f" · {subtitle}"
            ctx.draw.text((ctx.x_offset + int(10 * ctx.scale), y), line[:52], fill=EINK_FG, font=font)
            y += font_size + int(3 * ctx.scale)
    ctx.y = y
