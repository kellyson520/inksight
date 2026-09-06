"""
通用 JSON 模式渲染引擎
根据 JSON layout 定义将内容渲染为墨水屏图像
"""
from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx
from PIL import Image, ImageDraw, UnidentifiedImageError

from .config import (
    SCREEN_WIDTH, SCREEN_HEIGHT,
    EINK_4COLOR_PALETTE, EINK_COLOR_NAME_MAP, EINK_COLOR_AVAILABILITY,
)
from .patterns.utils import (
    EINK_BG,
    EINK_FG,
    apply_text_fontmode,
    draw_status_bar,
    draw_footer,
    draw_dashed_line,
    load_font,
    load_font_by_name,
    paste_icon_onto,
    load_icon,
    wrap_text,
    wrap_text_fill_sidebar,
    has_cjk,
    safe_font_bbox,
)
from .layout_presets import expand_layout_presets
from .mode_catalog import builtin_catalog_map
from .image_processing import convert_image_block
from .blocks.spec import BlockSpec

logger = logging.getLogger(__name__)

# Cap component-tree scaling on wide panels so preset pt sizes stay near the bitmap PCF grid
# (see patterns.utils INKSIGHT_BITMAP_MAX_REQUEST_SIZE). width >= LARGE_PANEL_MIN_W covers
# 583-inch class (648 px) and 7.5-inch class (800 px) bodies.
_COMPONENT_TREE_SCALE_CAP = float(
    os.getenv(
        "INKSIGHT_COMPONENT_TREE_SCALE_MAX",
        os.getenv("INKSIGHT_648_COMPONENT_SCALE_MAX", "1.35"),
    )
)
_LARGE_PANEL_MIN_W = int(os.getenv("INKSIGHT_LARGE_PANEL_MIN_WIDTH", "648"))

_BACKEND_ROOT = Path(__file__).resolve().parent.parent
_UPLOAD_DIR = _BACKEND_ROOT / "runtime_uploads"

STATUS_BAR_BOTTOM_DEFAULT = 36  # Used when screen_h unknown (e.g. dataclass default)

_EMOJI_PATTERN = re.compile(
    r"[\U0001F300-\U0001F9FF\u2600-\u26FF\u2700-\u27BF]+", re.UNICODE
)


def _strip_emoji(s: str) -> str:
    """Remove emoji/symbols that typical CJK fonts don't render."""
    if not s:
        return s
    return _EMOJI_PATTERN.sub("", s).strip()


def _num(v: Any) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


_LABEL_EMOJI_TO_ICON = {
    "\U0001f4d6": "book",
    "\U0001f4a1": "tips",
    "\U0001f31f": "star",
}

_BUILTIN_STATIC_ATTRIBUTIONS = {
    "zh": {
        "ARTWALL": "— 墨上观形",
        "BIAS": "— 见自己",
        "BRIEFING": "— 科技改变生活",
        "CALENDAR": "— 日有其序",
        "CHALLENGE": "— 试试看",
        "COUNTDOWN": "— 静待那天",
        "DAILY": "— 活在当下",
        "FITNESS": "— 动起来",
        "LIFEBAR": "— 此刻即刻度",
        "QUESTION": "— 想一想",
        "RECIPE": "— 好好吃饭",
        "RIDDLE": "— 且猜且想",
        "ROAST": "— 一笑了之",
        "STORY": "— 微光成篇",
        "THISDAY": "— 以史为镜",
        "TIMETABLE": "— 按表前行",
        "WEATHER": "— 阴晴有时",
        "WORD_OF_THE_DAY": "— 每日精进",
        "POMODORO": "— 专注当下",
        "DRINK_WATER": "— 保持水润",
        "SERVER_STATUS": "— 守护在线",
    },
    "en": {
        "ARTWALL": "— Ink Art",
        "BIAS": "— Think Clearly",
        "BRIEFING": "— Tech Brief",
        "CALENDAR": "— InkSight",
        "CHALLENGE": "— Just Do It",
        "COUNTDOWN": "— Remember",
        "DAILY": "— Carpe Diem",
        "FITNESS": "— Stay Healthy",
        "LIFEBAR": "— Time Flies",
        "QUESTION": "— Take a Moment",
        "RECIPE": "— Eat Well",
        "RIDDLE": "— Think About It",
        "ROAST": "— InkSight AI",
        "STORY": "— Micro Fiction",
        "THISDAY": "— History",
        "TIMETABLE": "— InkSight",
        "WEATHER": "— Open-Meteo",
        "WORD_OF_THE_DAY": "— Expand Your Lexicon",
        "POMODORO": "— Deep Focus",
        "DRINK_WATER": "— Stay Hydrated",
        "SERVER_STATUS": "— Always Online",
    },
}


def _section_icon_from_label(label: str) -> str | None:
    """If label starts with a known emoji, return the corresponding icon name."""
    for emoji, icon_name in _LABEL_EMOJI_TO_ICON.items():
        if label.startswith(emoji) or emoji in label:
            return icon_name
    return None


def _localized_footer_label(mode_id: str, fallback_label: str, language: str) -> str:
    item = builtin_catalog_map().get((mode_id or "").upper())
    if not item:
        return fallback_label
    return item.en.name if language == "en" else item.zh.name


def _localized_footer_attribution(mode_id: str, attribution: str, language: str) -> str:
    if not attribution or "{" in attribution:
        return attribution
    localized = _BUILTIN_STATIC_ATTRIBUTIONS.get(language, {}).get((mode_id or "").upper())
    return localized or attribution


def _resolve_template(content: dict, template: str) -> str:
    def _replace(m: re.Match) -> str:
        key = m.group(1)
        val = content.get(key, "")
        if isinstance(val, list):
            return ", ".join(str(v) for v in val)
        return str(val)
    return re.sub(r"\{(\w+)\}", _replace, template)


def _resolve_named_color(ctx: RenderContext, color_name: Any, default: int = EINK_FG) -> int:
    if not isinstance(color_name, str) or not color_name:
        return default
    return ctx.color_index(color_name, default)


@dataclass
class RenderContext:
    """Mutable state threaded through block renderers."""
    draw: ImageDraw.ImageDraw
    img: Image.Image
    content: dict
    screen_w: int = SCREEN_WIDTH
    screen_h: int = SCREEN_HEIGHT
    y: int = STATUS_BAR_BOTTOM_DEFAULT
    x_offset: int = 0
    available_width: int = SCREEN_WIDTH
    footer_height: int = 30
    colors: int = 2
    footer_top_offset: int = 0

    @property
    def scale(self) -> float:
        return max(0.92, self.screen_w / 400.0)

    @property
    def h_scale(self) -> float:
        return self.screen_h / 300.0

    @property
    def min_scale(self) -> float:
        """Conservative scale factor based on the more constrained dimension."""
        return max(0.65, min(self.scale, self.h_scale))

    def __post_init__(self):
        if self.available_width == SCREEN_WIDTH and self.screen_w != SCREEN_WIDTH:
            self.available_width = self.screen_w

    @property
    def footer_top(self) -> int:
        return self.screen_h - self.footer_height + self.footer_top_offset

    def resolve(self, template: str) -> str:
        """Resolve {field} placeholders against content dict."""
        return _resolve_template(self.content, template)

    def get_field(self, name: str) -> Any:
        return self.content.get(name, "")

    @property
    def remaining_height(self) -> int:
        return self.footer_top - self.y

    def color_index(self, name: str, default: int = EINK_FG) -> int:
        """Return palette index for a named color if the device supports it."""
        available = EINK_COLOR_AVAILABILITY.get(self.colors, frozenset())
        if name not in available:
            return default
        return EINK_COLOR_NAME_MAP.get(name, default)

    def resolve_color(self, block: dict, default: int = EINK_FG) -> int:
        """Resolve block 'color' property to a fill value."""
        name = block.get("color")
        if not name:
            return default
        return self.color_index(name, default)

    def paste_icon(self, icon: Image.Image, pos: tuple[int, int], fill: int = EINK_FG) -> None:
        """Paste a 1-bit icon onto the canvas, handling palette mode transparency."""
        paste_icon_onto(self.img, icon, pos, fill)



# ── Component Tree Engine 下沉模块 ─────────────────────────────
from core.component_tree_engine import (
    ComponentBox,
    ComponentNode,
    _render_component_tree_mode,
    _uses_component_tree,
    _merge_layout_dict,
    _component_aligned_y,
)

# ── Decorations ──────────────────────────────────────────────


def _load_decoration_image(
    name: str, size: tuple[int, int], *,
    image_mode: str = "auto", dither: bool = False,
) -> Image.Image | None:
    """Load a decoration image, converting to 1-bit for e-ink display.

    image_mode controls the processing algorithm:
      "circle"        - crop to circle with border, keep content inside
      "invert"        - invert colors (for dark-bg icons with white content)
      "invert_dither" - dither then invert bg to white (best for dark-bg detail)
      "color_dither"  - remove colored bg via floodfill then dither (colored-bg icons)
      "auto"          - threshold/dither with transparent white areas
    """
    path = _BACKEND_ROOT / "fonts" / "icons" / f"{name}.png"
    if not path.exists():
        return None
    src = Image.open(path).convert("RGBA")
    src = src.resize(size, Image.LANCZOS)
    w, h = size
    gray = src.convert("L")

    if image_mode == "circle":
        from PIL import ImageDraw as PilDraw
        r = min(w, h) // 2
        cx, cy = w // 2, h // 2
        circle_mask = Image.new("L", size, 0)
        md = PilDraw.Draw(circle_mask)
        md.ellipse((cx - r, cy - r, cx + r, cy + r), fill=255)
        content = gray.point(lambda v: 0 if v < 192 else 255, "1")
        result = Image.new("1", size, 1)
        result.paste(content, mask=circle_mask)
        rd = ImageDraw.Draw(result)
        rd.ellipse((cx - r, cy - r, cx + r, cy + r), outline=0, width=1)
        return result

    if image_mode == "invert":
        inverted = gray.point(lambda v: 0 if v > 128 else 255, "1")
        alpha = gray.point(lambda v: 255 if v > 64 else 0, "L")
        result = Image.new("1", size, 1)
        result.paste(inverted, mask=alpha)
        return result

    if image_mode == "invert_dither":
        from PIL import ImageDraw as PilDraw
        clean = gray.copy()
        for corner in [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)]:
            if clean.getpixel(corner) < 30:
                PilDraw.floodfill(clean, corner, 255, thresh=30)
        return clean.convert("1")

    if image_mode == "color_dither":
        from PIL import ImageDraw as PilDraw
        clean = gray.copy()
        bg_val = sum(clean.getpixel(c) for c in [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)]) // 4
        thresh = 40
        for corner in [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)]:
            if abs(clean.getpixel(corner) - bg_val) <= thresh:
                PilDraw.floodfill(clean, corner, 255, thresh=thresh)
        return clean.convert("1")

    if dither:
        mono = gray.convert("1")
        alpha = gray.point(lambda v: 255 if v < 220 else 0, "L")
    else:
        mono = gray.point(lambda v: 0 if v < 128 else 255, "1")
        alpha = gray.point(lambda v: 255 if v < 200 else 0, "1")
    result = Image.new("1", size, 1)
    result.paste(mono, mask=alpha)
    return result


def _apply_decorations(
    img: Image.Image,
    decorations: list[dict],
    screen_w: int,
    screen_h: int,
    status_bar_bottom: int,
) -> None:
    """Paste decoration images at absolute positions."""
    if not decorations:
        return
    scale = screen_w / 400.0
    for dec in decorations:
        icon_name = dec.get("icon")
        if not icon_name:
            continue
        size = int(dec.get("size", 36) * scale)
        dither = dec.get("dither", False)
        image_mode = dec.get("image_mode", "auto")
        dec_img = _load_decoration_image(
            icon_name, (size, size), image_mode=image_mode, dither=dither,
        )
        if dec_img is None:
            continue
        margin = int(dec.get("margin", 8) * scale)
        anchor = dec.get("anchor", "top_left")
        if anchor == "top_left":
            x, y = margin, status_bar_bottom + margin
        elif anchor == "top_right":
            x, y = screen_w - size - margin, status_bar_bottom + margin
        elif anchor == "bottom_left":
            x, y = margin, screen_h - size - margin
        elif anchor == "bottom_right":
            x, y = screen_w - size - margin, screen_h - size - margin
        else:
            x, y = margin, status_bar_bottom + margin
        paste_icon_onto(img, dec_img, (x, y))


# ── Public API ───────────────────────────────────────────────


def render_json_mode(
    mode_def: dict,
    content: dict,
    *,
    date_str: str,
    weather_str: str,
    battery_pct: float,
    weather_code: int = -1,
    time_str: str = "",
    screen_w: int = SCREEN_WIDTH,
    screen_h: int = SCREEN_HEIGHT,
    colors: int = 2,
    language: str = "zh",
) -> Image.Image:
    """Render a JSON-defined mode to an e-ink image (1-bit or 4-color palette)."""
    if colors >= 3:
        img = Image.new("P", (screen_w, screen_h), EINK_BG)
        pal = EINK_4COLOR_PALETTE + [0] * (768 - len(EINK_4COLOR_PALETTE))
        img.putpalette(pal)
    else:
        img = Image.new("1", (screen_w, screen_h), EINK_BG)
    draw = ImageDraw.Draw(img)
    apply_text_fontmode(draw)
    layout = mode_def.get("layout", {})
    overrides = mode_def.get("layout_overrides", {})
    size_key = f"{screen_w}x{screen_h}"
    if size_key in overrides:
        layout = _merge_layout_dict(layout, overrides[size_key])
    layout = expand_layout_presets(layout)

    sb = layout.get("status_bar", {})
    ft_layout = layout.get("footer", {})
    status_bar_pct = 0.10 if screen_h < 200 else 0.12
    # 296×128：旧 draw_status_bar 横线在 int(h*0.11)（约 14px）；若用 int(h*0.10)+2 与之相同，视觉上“没下移”
    if screen_h <= 128:
        status_bar_bottom = int(screen_h * 0.11) + 2
    else:
        status_bar_bottom = int(screen_h * status_bar_pct)

    _dsb_kw: dict[str, Any] = dict(
        draw=draw,
        img=img,
        date_str=date_str,
        weather_str=weather_str,
        battery_pct=int(battery_pct),
        weather_code=weather_code,
        line_width=sb.get("line_width", 1),
        dashed=sb.get("dashed", False),
        time_str=time_str,
        screen_w=screen_w,
        screen_h=screen_h,
        colors=colors,
        language=language,
    )
    if screen_h <= 128:
        _dsb_kw["separator_y"] = status_bar_bottom
    draw_status_bar(**_dsb_kw)

    scale = screen_w / 400.0
    if scale < 0.92:
        scale = 0.92
    min_scale = min(scale, screen_h / 300.0)
    if min_scale < 0.65:
        min_scale = 0.65
    footer_height = int(ft_layout.get("height", 30) * min_scale)
    # 2.9"（128px 高等）：页脚要容纳图标 + 左右文案，缩放后仍须足够高度，否则会贴底
    if screen_h <= 128:
        footer_height = max(footer_height, 24)
    footer_top = screen_h - footer_height
    # 页脚顶部分隔线相对「内容上边界」下移 2–3px，与 draw_footer(y_line) 一致
    footer_top_offset = 0
    if screen_h <= 128:
        footer_top_offset = 3
        footer_top += footer_top_offset

    body = layout.get("body", [])
    if _uses_component_tree(body, layout):
        theme = dict(layout.get("component_theme", {}))
        if "debug_overlay" in layout:
            theme["debug_overlay"] = layout.get("debug_overlay")
        ctx = _render_component_tree_mode(
            draw,
            img,
            content,
            body,
            theme,
            screen_w=screen_w,
            screen_h=screen_h,
            status_bar_bottom=status_bar_bottom,
            footer_height=footer_height,
            footer_top_offset=footer_top_offset,
            colors=colors,
        )
    else:
        body_align = layout.get("body_align", "center")
        _has_vcenter = any(
            b.get("type") == "centered_text" and b.get("vertical_center", True)
            for b in body
        )

        if _has_vcenter and len(body) == 1:
            ctx = RenderContext(
                draw=draw, img=img, content=content,
                screen_w=screen_w, screen_h=screen_h,
                y=status_bar_bottom, footer_height=footer_height, footer_top_offset=footer_top_offset, colors=colors,
            )
            _render_centered_text(ctx, body[0], use_full_body=True)
        elif body_align == "center" and body:
            measure_img = Image.new("1", (screen_w, screen_h), EINK_BG)
            measure_ctx = RenderContext(
                draw=ImageDraw.Draw(measure_img), img=measure_img, content=content,
                screen_w=screen_w, screen_h=screen_h,
                y=status_bar_bottom, footer_height=footer_height, footer_top_offset=footer_top_offset,
            )
            apply_text_fontmode(measure_ctx.draw)
            for block in body:
                if measure_ctx.y >= footer_top - 10:
                    break
                BlockSpec.from_dict(block).measure(measure_ctx, screen_w)
            content_height = measure_ctx.y - status_bar_bottom
            available_height = footer_top - status_bar_bottom
            offset = max(0, (available_height - content_height) // 2)

            ctx = RenderContext(
                draw=draw, img=img, content=content,
                screen_w=screen_w, screen_h=screen_h,
                y=status_bar_bottom + offset, footer_height=footer_height, footer_top_offset=footer_top_offset,
                colors=colors,
            )
            for block in body:
                if ctx.y >= footer_top - 10:
                    break
                BlockSpec.from_dict(block).render(ctx)
        else:
            ctx = RenderContext(
                draw=draw, img=img, content=content,
                screen_w=screen_w, screen_h=screen_h,
                y=status_bar_bottom, footer_height=footer_height, footer_top_offset=footer_top_offset, colors=colors,
            )
            for block in body:
                if ctx.y >= footer_top - 10:
                    break
                BlockSpec.from_dict(block).render(ctx)

    _apply_decorations(img, layout.get("decorations", []), screen_w, screen_h, status_bar_bottom)

    ft = ft_layout
    mode_id = mode_def.get("mode_id", "")
    label = _localized_footer_label(mode_id, ft.get("label", mode_id), language)
    attribution = ctx.resolve(ft.get("attribution_template", "")) if ft.get("attribution_template") else ""
    attribution = _localized_footer_attribution(mode_id, attribution, language)
    _attr_font_size = ft.get("font_size")
    if _attr_font_size is not None:
        _attr_font_size = int(_attr_font_size * scale)
    draw_footer(
        draw, img, label, attribution,
        mode_id=mode_id,
        weather_code=content.get("today_code", content.get("code")),
        line_width=ft.get("line_width", 1),
        dashed=ft.get("dashed", False),
        attr_font_size=_attr_font_size,
        screen_w=screen_w, screen_h=screen_h,
        colors=colors,
        footer_top=footer_top,
    )

    return img



# ── Block Dispatcher & Sub-module Re-exports ─────────────────────────────────
from .blocks import (
    RenderContext,
    STATUS_BAR_BOTTOM_DEFAULT,
    BLOCK_RENDERERS as _BLOCK_RENDERERS,
    render_block as _render_block,
    measure_block_size as _measure_block_size,
    measure_column_blocks_height as _measure_column_blocks_height,
    slice_calendar_rows_around_day,
    resolve_template as _resolve_template,
    resolve_named_color as _resolve_named_color,
    section_icon_from_label as _section_icon_from_label,
    strip_emoji as _strip_emoji,
)
from .blocks.text import (
    render_centered_text as _render_centered_text,
    render_text as _render_text,
    render_list as _render_list,
    render_icon_text as _render_icon_text,
    render_weather_icon_text as _render_weather_icon_text,
    render_big_number as _render_big_number,
    render_key_value as _render_key_value,
    render_icon_list as _render_icon_list,
    render_weather_icon as _render_weather_icon,
    pick_cjk_font as _pick_cjk_font,
)
from .blocks.layout import (
    render_separator as _render_separator,
    render_section as _render_section,
    render_vertical_stack as _render_vertical_stack,
    render_conditional as _render_conditional,
    render_spacer as _render_spacer,
    render_two_column as _render_two_column,
    render_group as _render_group,
    render_flex_row as _render_flex_row,
    render_card as _render_card,
)
from .blocks.components import (
    render_badge as _render_badge,
    render_badge_group as _render_badge_group,
    render_metric_card as _render_metric_card,
    render_segmented_row as _render_segmented_row,
    render_striped_table as _render_striped_table,
    render_progress_bar as _render_progress_bar,
    render_rating_choices as _render_rating_choices,
    render_image as _render_image,
)
from .blocks.charts import (
    render_sparkline as _render_sparkline,
    render_temp_chart as _render_temp_chart,
    render_forecast_cards as _render_forecast_cards,
)
from .blocks.grids import (
    render_grid as _render_grid,
    render_calendar_grid as _render_calendar_grid,
    render_timetable_grid as _render_timetable_grid,
)

__all__ = [
    "render_json_mode",
    "RenderContext",
    "_BLOCK_RENDERERS",
    "_render_block",
    "_measure_block_size",
    "_measure_column_blocks_height",
    "slice_calendar_rows_around_day",
]
