"""Full-bleed game giveaway cover with corner labels."""
from __future__ import annotations

from core.patterns.utils import EINK_BG, EINK_FG, has_cjk, load_font
from .components import render_image
from .context import RenderContext
from .registry import register_block


def _text(ctx: RenderContext, value: object) -> str:
    return ctx.resolve(str(value or "")).strip()


def _badge(ctx: RenderContext, text: str, x: int, y: int, *, align: str = "left", font_size: int = 11) -> None:
    if not text:
        return
    font_name = "noto_serif_bold"
    if has_cjk(text):
        font_name = "noto_serif_bold"
    font = load_font(font_name, max(8, int(font_size * ctx.scale)))
    bbox = font.getbbox(text)
    pad_x = max(4, int(7 * ctx.scale))
    pad_y = max(2, int(3 * ctx.scale))
    width = bbox[2] - bbox[0] + pad_x * 2
    height = max(font_size, bbox[3] - bbox[1]) + pad_y * 2
    if align == "right":
        x -= width
    ctx.draw.rounded_rectangle([x, y, x + width, y + height], radius=max(2, height // 4), fill=EINK_FG)
    ctx.draw.text((x + pad_x - bbox[0], y + pad_y - bbox[1]), text, font=font, fill=EINK_BG)


@register_block("game_giveaway")
def render_game_giveaway(ctx: RenderContext, block: dict) -> None:
    width = min(ctx.available_width, int(block.get("width", ctx.available_width)))
    height = int(block.get("height", max(20, ctx.footer_top - ctx.y - 4)))
    x = ctx.x_offset + max(0, (ctx.available_width - width) // 2)
    y = ctx.y
    render_image(ctx, {
        "field": block.get("cover_field", "cover_url"),
        "width": width,
        "height": height,
        "x": x,
        "y": y,
        "fit": block.get("fit", "cover"),
        "margin_bottom": 0,
    })
    source = _text(ctx, ctx.get_field(block.get("source_field", "source_label")))
    deadline = _text(ctx, ctx.get_field(block.get("deadline_field", "deadline_label")))
    title = _text(ctx, ctx.get_field(block.get("title_field", "game_title")))
    margin = max(4, int(block.get("margin", 8) * ctx.scale))
    _badge(ctx, source, x + margin, y + margin, font_size=int(block.get("source_font_size", 11)))
    _badge(ctx, deadline, x + width - margin, y + margin, align="right", font_size=int(block.get("deadline_font_size", 9)))
    _badge(ctx, title, x + margin, y + height - margin - int(26 * ctx.scale), font_size=int(block.get("title_font_size", 14)))
    ctx.y = y + height + int(block.get("margin_bottom", 6) * ctx.scale)
