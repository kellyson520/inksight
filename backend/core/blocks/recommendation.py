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
    items_to_render = items[:1] if style == "cover_card" else items[:max_items]
    for index, item in enumerate(items_to_render, 1):
        if not isinstance(item, dict): continue
        title = str(item.get("title", "推荐")).strip()
        subtitle = str(item.get("subtitle", "")).strip()
        rank = str(item.get("rank_label") or f"NO.{index}")
        if style == "cover_card":
            image_data = item.get("image_data")
            image_url = str(item.get("thumbnail_url") or item.get("cover_url") or "").strip()
            max_allowed = max(40, ctx.screen_h - ctx.footer_height - y - int(4 * ctx.scale))
            card_h_prop = int(block.get("card_height", 0) * ctx.scale)
            if card_h_prop > 0:
                card_height = min(card_h_prop, max_allowed)
            else:
                card_height = max_allowed

            if image_data is not None or image_url:
                previous_image = ctx.content.get("__recommendation_image")
                ctx.content["__recommendation_image"] = image_data if image_data is not None else image_url
                # Draw image: reserve space for text and margins below image
                text_block_h = font_size + int(4 * ctx.scale)
                img_h = max(16, card_height - text_block_h - int(2 * ctx.scale))
                render_image(ctx, {"field": "__recommendation_image", "width": max(20, ctx.available_width - int(20 * ctx.scale)), "height": img_h, "x": ctx.x_offset + int(10 * ctx.scale), "y": y, "fit": "contain"})
                if previous_image is None:
                    ctx.content.pop("__recommendation_image", None)
                else:
                    ctx.content["__recommendation_image"] = previous_image

            line = f"{rank}  {title}"
            if subtitle and len(line) < 30 and ctx.available_width > 240:
                line += f" · {subtitle}"
            # Render title/author line directly below image area, well within card_height
            text_y = y + card_height - font_size - int(2 * ctx.scale)
            max_chars = max(10, int((ctx.available_width - int(20 * ctx.scale)) / (font_size * 0.72)))
            ctx.draw.text((ctx.x_offset + int(10 * ctx.scale), text_y), line[:max_chars], fill=EINK_FG, font=bold)
            y += card_height + int(2 * ctx.scale)
        else:
            line = f"{rank}  {title}"
            if subtitle: line += f" · {subtitle}"
            max_chars = max(10, int((ctx.available_width - int(20 * ctx.scale)) / (font_size * 0.72)))
            ctx.draw.text((ctx.x_offset + int(10 * ctx.scale), y), line[:max_chars], fill=EINK_FG, font=font)
            y += font_size + int(3 * ctx.scale)
    ctx.y = y
