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


@dataclass
class ComponentBox:
    x: int
    y: int
    width: int
    height: int


@dataclass
class ComponentNode:
    kind: str
    props: dict
    content: dict
    children: list["ComponentNode"] = field(default_factory=list)
    box: ComponentBox | None = None
    measured_width: int = 0
    measured_height: int = 0
    draw_data: dict[str, Any] = field(default_factory=dict)


def _component_aligned_y(box_y: int, box_height: int, content_height: int, align_y: str) -> int:
    extra = max(0, box_height - content_height)
    if align_y == "center":
        return box_y + extra // 2
    if align_y in {"bottom", "end"}:
        return box_y + extra
    return box_y


def _debug_outline_color(ctx: RenderContext) -> int:
    return 3 if ctx.img.mode == "P" else EINK_FG


def _debug_bbox_color(ctx: RenderContext) -> int:
    return 2 if ctx.img.mode == "P" else EINK_FG


def _draw_debug_rect(ctx: RenderContext, rect: tuple[int, int, int, int], *, color: int) -> None:
    x0, y0, x1, y1 = rect
    if x1 <= x0 or y1 <= y0:
        return
    ctx.draw.rectangle([x0, y0, x1 - 1, y1 - 1], outline=color, width=1)


def _paint_component_debug_overlay(ctx: RenderContext, node: ComponentNode) -> None:
    box = node.box
    if box is None:
        return
    _draw_debug_rect(
        ctx,
        (box.x, box.y, box.x + box.width, box.y + box.height),
        color=_debug_outline_color(ctx),
    )
    if node.kind == "text":
        font = node.draw_data.get("font")
        lines = node.draw_data.get("lines", [])
        line_height = node.draw_data.get("line_height", 0)
        total_height = len(lines) * line_height if lines else 0
        if font is not None and lines and line_height > 0:
            align = node.props.get("align", "left")
            align_y = node.props.get("align_y", "top")
            try:
                ink_dy_dbg = int(node.props.get("ink_offset_y", 0) or 0)
            except (TypeError, ValueError):
                ink_dy_dbg = 0
            y = _component_aligned_y(box.y, box.height, total_height, align_y) + ink_dy_dbg
            for line in lines:
                bbox = font.getbbox(line)
                line_width = bbox[2] - bbox[0]
                if align == "center":
                    x = box.x + max(0, (box.width - line_width) // 2)
                elif align == "right":
                    x = box.x + max(0, box.width - line_width)
                else:
                    x = box.x
                _draw_debug_rect(
                    ctx,
                    (x + bbox[0], y + bbox[1], x + bbox[2], y + bbox[3]),
                    color=_debug_bbox_color(ctx),
                )
                y += line_height
    elif node.kind == "big_number":
        bbox = node.draw_data.get("bbox")
        text = node.draw_data.get("text", "")
        if bbox and text:
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            align = node.props.get("align", "center")
            align_y = node.props.get("align_y", "top")
            if align == "left":
                x = box.x - bbox[0]
            elif align == "right":
                x = box.x + max(0, box.width - text_width) - bbox[0]
            else:
                x = box.x + max(0, (box.width - text_width) // 2) - bbox[0]
            ink_top = _component_aligned_y(box.y, box.height, text_height, align_y)
            y = ink_top - bbox[1]
            _draw_debug_rect(
                ctx,
                (x + bbox[0], y + bbox[1], x + bbox[2], y + bbox[3]),
                color=_debug_bbox_color(ctx),
            )
    for child in node.children:
        _paint_component_debug_overlay(ctx, child)


def _merge_layout_dict(base: dict, override: dict) -> dict:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merge_layout_dict(merged[key], value)
        else:
            merged[key] = value
    return merged


def _uses_component_tree(body: Any, layout: dict) -> bool:
    if layout.get("layout_engine") == "component_tree":
        return True
    if isinstance(body, dict):
        return body.get("type") in {"column", "row", "repeat", "section_box", "box", "float_wrap"}
    return False


def _scaled_value(value: Any, scale: float, default: int = 0, minimum: int = 0) -> int:
    raw = value if isinstance(value, (int, float)) else default
    return max(minimum, int(raw * scale))


def _component_tree_scale(ctx: RenderContext, theme: dict) -> float:
    """Return the effective component-tree scale.

    Raw ctx.scale grows with screen width (e.g. 648 px -> 1.62). Applying that fully to font
    sizes pushes past PCF bitmap coverage and falls back to blurry TTF on e-ink. For wide
    panels (screen_w >= INKSIGHT_LARGE_PANEL_MIN_WIDTH) we cap by INKSIGHT_COMPONENT_TREE_SCALE_MAX
    (default 1.35, same legacy cap as the old 648-only branch). Modes may set layout.component_scale.
    """
    raw = ctx.scale
    override = theme.get("component_scale") or theme.get("scale")
    if override is not None:
        try:
            return max(0.65, float(override))
        except (TypeError, ValueError):
            pass
    if ctx.screen_w >= _LARGE_PANEL_MIN_W:
        return min(raw, _COMPONENT_TREE_SCALE_CAP)
    return raw


def _component_grow(node: ComponentNode) -> int:
    grow = node.props.get("grow", node.props.get("flex_grow", 0))
    try:
        return max(0, int(grow))
    except (TypeError, ValueError):
        return 0


def _component_text_value(node: ComponentNode) -> str:
    field_name = node.props.get("field")
    template = node.props.get("template")
    text = node.props.get("text")
    if field_name:
        value = node.content.get(field_name, "")
        if isinstance(value, list):
            return ", ".join(str(v) for v in value)
        return str(value)
    if template:
        return _resolve_template(node.content, template)
    if text:
        return _resolve_template(node.content, str(text))
    return ""


def _component_padding(props: dict, scale: float) -> tuple[int, int, int, int]:
    px = _scaled_value(props.get("padding_x"), scale)
    py = _scaled_value(props.get("padding_y"), scale)
    left = _scaled_value(props.get("padding_left"), scale, px)
    right = _scaled_value(props.get("padding_right"), scale, px)
    top = _scaled_value(props.get("padding_top"), scale, py)
    bottom = _scaled_value(props.get("padding_bottom"), scale, py)
    return left, top, right, bottom


def _component_fixed_width(node: ComponentNode, scale: float) -> int:
    return _scaled_value(node.props.get("width"), scale)


def _component_load_font(node: ComponentNode, text: str, theme: dict, scale: float, default_font: str, default_size: int) -> tuple[Any, int]:
    font_size = _scaled_value(node.props.get("font_size"), scale, default_size, 6)
    font_name = node.props.get("font_name")
    font_key = node.props.get("font", theme.get("body_font", default_font))
    if font_name:
        if has_cjk(text) and "Noto" not in font_name:
            font_name = "NotoSerifSC-Regular.ttf"
        return load_font_by_name(font_name, font_size), font_size
    if has_cjk(text):
        font_key = _pick_cjk_font(font_key)
    return load_font(font_key, font_size), font_size


def _fit_line_with_ellipsis(text: str, font: Any, max_width: int) -> str:
    if max_width <= 0:
        return "..."
    b0 = safe_font_bbox(font, text)
    if b0[2] - b0[0] <= max_width:
        return text
    ellipsis = "..."
    eb = safe_font_bbox(font, ellipsis)
    if eb[2] - eb[0] > max_width:
        return ellipsis
    trimmed = text.rstrip(". ")
    while trimmed:
        candidate = trimmed.rstrip() + ellipsis
        cb = safe_font_bbox(font, candidate)
        if cb[2] - cb[0] <= max_width:
            return candidate
        trimmed = trimmed[:-1]
    return ellipsis


def _component_measure_text(node: ComponentNode, available_width: int | None, theme: dict, scale: float) -> None:
    text = _component_text_value(node)
    if not text:
        node.measured_width = 0
        node.measured_height = 0
        node.draw_data = {"lines": [], "font": None, "line_height": 0}
        return
    font, font_size = _component_load_font(node, text, theme, scale, "noto_serif_regular", theme.get("body_font_size", 12))
    max_lines = node.props.get("max_lines")
    ellipsis = node.props.get("ellipsis", True)
    if available_width is None:
        lines = [text]
    else:
        lines = wrap_text(text, font, max(1, available_width))
    if max_lines and len(lines) > max_lines:
        lines = lines[:max_lines]
        if lines and ellipsis:
            lines[-1] = _fit_line_with_ellipsis(lines[-1], font, max(1, available_width or 0))
    line_height = _scaled_value(node.props.get("line_height"), scale, font_size + theme.get("body_line_gap", 4), 1)
    text_width = 0
    for line in lines:
        bbox = safe_font_bbox(font, line)
        text_width = max(text_width, bbox[2] - bbox[0])
    node.measured_width = available_width if available_width is not None else text_width
    node.measured_height = len(lines) * line_height if lines else 0
    node.draw_data = {
        "lines": lines,
        "font": font,
        "line_height": line_height,
        "text_width": text_width,
        "text_height": len(lines) * line_height if lines else 0,
    }


def _measure_component_big_number(node: ComponentNode, theme: dict, scale: float) -> None:
    text = _component_text_value(node)
    if not text or text == "--":
        node.measured_width = 0
        node.measured_height = 0
        node.draw_data = {"font": None, "text": ""}
        return
    unit = str(node.props.get("unit", "") or "")
    if unit:
        text = f"{text}{unit}"
    font, font_size = _component_load_font(node, text, theme, scale, "noto_serif_bold", 42)
    bbox = font.getbbox(text)
    node.measured_width = max(0, bbox[2] - bbox[0])
    node.measured_height = max(0, bbox[3] - bbox[1])
    node.draw_data = {"font": font, "text": text, "bbox": bbox}


def _measure_component_progress_bar(node: ComponentNode, scale: float) -> None:
    width = _scaled_value(node.props.get("width"), scale, 80, 4)
    height = _scaled_value(node.props.get("height"), scale, 6, 2)
    node.measured_width = width
    node.measured_height = height
    node.draw_data = {"width": width, "height": height}


def _measure_component_separator(node: ComponentNode, available_width: int | None, scale: float) -> None:
    line_width = max(1, int(node.props.get("line_width", 1)))
    width = available_width if available_width is not None else _scaled_value(node.props.get("width"), scale, 60, 4)
    node.measured_width = max(0, width)
    node.measured_height = line_width
    node.draw_data = {"line_width": line_width}


def _build_component_node(defn: dict, content: dict) -> ComponentNode:
    kind = defn.get("type", "")
    if kind == "repeat":
        items = content.get(defn.get("field", ""), [])
        if not isinstance(items, list):
            items = []
        limit = defn.get("limit", defn.get("max_items", len(items)))
        try:
            lim_int = int(limit) if limit is not None else len(items)
        except (TypeError, ValueError):
            lim_int = len(items)
        raw_items = items[:lim_int] if lim_int >= 0 else items
        pair_step = int(defn.get("pair_step", 1) or 1)
        pair_sep = str(defn.get("pair_separator", ""))
        if pair_step > 1 and raw_items:
            paired: list[Any] = []
            for i in range(0, len(raw_items), pair_step):
                chunk = raw_items[i : i + pair_step]
                if not chunk:
                    continue
                if all(isinstance(x, str) for x in chunk):
                    paired.append(pair_sep.join(chunk))
                else:
                    paired.extend(chunk)
            items = paired
        else:
            items = raw_items
        item_def = defn.get("item")
        children: list[ComponentNode] = []
        if isinstance(item_def, dict):
            for idx, item in enumerate(items):
                item_content = dict(content)
                item_content["index"] = idx + 1
                item_content["_item"] = item
                item_content["_value"] = item
                if isinstance(item, dict):
                    item_content.update(item)
                children.append(_build_component_node(item_def, item_content))
        return ComponentNode(kind=kind, props=defn, content=content, children=children)
    children = [
        _build_component_node(child, content)
        for child in defn.get("children", [])
        if isinstance(child, dict)
    ]
    return ComponentNode(kind=kind, props=defn, content=content, children=children)


def _float_wrap_field_text(node: ComponentNode) -> str:
    field_name = node.props.get("text_field") or node.props.get("field")
    if not field_name:
        return ""
    value = node.content.get(str(field_name), "")
    if isinstance(value, list):
        return ", ".join(str(v) for v in value)
    return str(value)


def _measure_float_wrap_node(node: ComponentNode, available_width: int | None, theme: dict, scale: float) -> None:
    gap = _scaled_value(node.props.get("gap"), scale, 4, 0)
    float_below_gap = _scaled_value(node.props.get("float_below_gap"), scale, 2, 0)
    inner_w = max(0, (available_width or 0))
    if not node.children:
        node.measured_width = inner_w
        node.measured_height = 0
        node.draw_data = {
            "gap": gap,
            "float_below_gap": float_below_gap,
            "float_w": 0,
            "float_h": 0,
            "side_lines": [],
            "below_lines": [],
            "font": None,
            "line_height": 0,
        }
        return
    fc = node.children[0]
    _measure_component_node(fc, available_width, theme, scale)
    fw, fh = fc.measured_width, fc.measured_height
    side_w = max(0, inner_w - fw - gap)
    text = _strip_emoji(_float_wrap_field_text(node))
    shim = ComponentNode(kind="text", props=node.props, content=node.content, children=[])
    font, font_size = _component_load_font(
        shim, text if text.strip() else " ",
        theme, scale,
        "noto_serif_regular",
        theme.get("body_font_size", 12),
    )
    line_height = _scaled_value(node.props.get("line_height"), scale, font_size + theme.get("body_line_gap", 4), 1)
    if not text.strip():
        node.measured_width = inner_w if inner_w > 0 else fw
        node.measured_height = fh
        node.draw_data = {
            "gap": gap,
            "float_below_gap": float_below_gap,
            "float_w": fw,
            "float_h": fh,
            "side_lines": [],
            "below_lines": [],
            "font": None,
            "line_height": line_height,
        }
        return
    side_lines, remainder = wrap_text_fill_sidebar(text, font, side_w, fh, line_height)
    below_w = max(1, inner_w - fw - gap) if inner_w > 0 else max(1, side_w or 1)
    below_lines = wrap_text(remainder, font, below_w) if remainder else []
    max_below = node.props.get("wrap_below_max_lines")
    if max_below is not None:
        try:
            mb = int(max_below)
            if mb >= 0 and len(below_lines) > mb:
                below_lines = below_lines[:mb]
                ellipsis = node.props.get("ellipsis", True)
                if below_lines and ellipsis:
                    below_lines[-1] = _fit_line_with_ellipsis(below_lines[-1], font, below_w)
        except (TypeError, ValueError):
            pass
    side_text_bottom = len(side_lines) * line_height
    if below_lines:
        text_stack_bottom = side_text_bottom + float_below_gap + len(below_lines) * line_height
        total_h = max(fh, text_stack_bottom)
    else:
        total_h = fh
    node.measured_width = inner_w if inner_w > 0 else fw + gap + max(side_w, 1)
    node.measured_height = total_h
    node.draw_data = {
        "gap": gap,
        "float_below_gap": float_below_gap,
        "float_w": fw,
        "float_h": fh,
        "below_x_shift": fw + gap,
        "below_text_width": below_w,
        "side_text_bottom": side_text_bottom,
        "side_lines": side_lines,
        "below_lines": below_lines,
        "font": font,
        "line_height": line_height,
    }


def _measure_component_node(node: ComponentNode, available_width: int | None, theme: dict, scale: float) -> None:
    if node.kind == "text":
        _component_measure_text(node, available_width, theme, scale)
        return
    if node.kind == "big_number":
        _measure_component_big_number(node, theme, scale)
        return
    if node.kind == "progress_bar":
        _measure_component_progress_bar(node, scale)
        return
    if node.kind == "separator":
        _measure_component_separator(node, available_width, scale)
        return
    if node.kind == "spacer":
        sh_raw = node.props.get("height", node.props.get("min_height", 6))
        sh = _scaled_value(sh_raw, scale, 6, 1)
        node.measured_width = available_width if available_width is not None else 0
        node.measured_height = max(0, int(sh))
        node.draw_data = {}
        return
    if node.kind == "repeat":
        gap = _scaled_value(node.props.get("gap"), scale)
        total_height = 0
        max_width = 0
        for idx, child in enumerate(node.children):
            _measure_component_node(child, available_width, theme, scale)
            total_height += child.measured_height
            if idx > 0:
                total_height += gap
            max_width = max(max_width, child.measured_width)
        node.measured_width = available_width if available_width is not None else max_width
        node.measured_height = total_height
        node.draw_data = {"gap": gap}
        return
    if node.kind == "column":
        left, top, right, bottom = _component_padding(node.props, scale)
        gap = _scaled_value(node.props.get("gap"), scale)
        inner_width = None if available_width is None else max(0, available_width - left - right)
        total_height = top + bottom
        max_width = 0
        visible_count = 0
        for child in node.children:
            _measure_component_node(child, inner_width, theme, scale)
            if child.measured_height <= 0 and child.measured_width <= 0:
                continue
            if visible_count > 0:
                total_height += gap
            total_height += child.measured_height
            visible_count += 1
            max_width = max(max_width, child.measured_width)
        fixed_width = _scaled_value(node.props.get("width"), scale)
        width = fixed_width or (available_width if available_width is not None else max_width + left + right)
        min_height = _scaled_value(node.props.get("min_height"), scale)
        fixed_height = _scaled_value(node.props.get("height"), scale)
        node.measured_width = width
        node.measured_height = max(total_height, min_height, fixed_height)
        node.draw_data = {
            "padding": (left, top, right, bottom),
            "gap": gap,
        }
        return
    if node.kind == "row":
        left, top, right, bottom = _component_padding(node.props, scale)
        gap = _scaled_value(node.props.get("gap"), scale)
        inner_width = None if available_width is None else max(0, available_width - left - right)
        total_gap = gap * max(0, len(node.children) - 1)
        fixed_width = 0
        grow_total = 0
        for child in node.children:
            if _component_grow(child) > 0:
                grow_total += _component_grow(child)
                continue
            child_width_hint = _component_fixed_width(child, scale) or None
            _measure_component_node(child, child_width_hint, theme, scale)
            fixed_width += child.measured_width
        remaining_width = max(0, (inner_width or 0) - fixed_width - total_gap)
        remaining_slots = grow_total
        for child in node.children:
            grow = _component_grow(child)
            if grow <= 0:
                continue
            child_width = remaining_width if remaining_slots <= grow else remaining_width * grow // remaining_slots
            _measure_component_node(child, child_width, theme, scale)
            remaining_width -= child_width
            remaining_slots -= grow
        content_width = fixed_width + total_gap + sum(
            child.measured_width for child in node.children if _component_grow(child) > 0
        )
        content_height = max((child.measured_height for child in node.children), default=0)
        fixed_width = _scaled_value(node.props.get("width"), scale)
        width = fixed_width or (available_width if available_width is not None else content_width + left + right)
        min_height = _scaled_value(node.props.get("min_height"), scale)
        fixed_height = _scaled_value(node.props.get("height"), scale)
        node.measured_width = width
        node.measured_height = max(content_height + top + bottom, min_height, fixed_height)
        node.draw_data = {
            "padding": (left, top, right, bottom),
            "gap": gap,
        }
        return
    if node.kind == "section_box":
        title = _resolve_template(node.content, str(node.props.get("title", "")))
        title_font_size = _scaled_value(node.props.get("title_font_size"), scale, theme.get("section_title_font_size", 12), 6)
        title_font_key = node.props.get("title_font", theme.get("section_title_font", "noto_serif_regular"))
        if has_cjk(title):
            title_font_key = _pick_cjk_font(title_font_key)
        title_font = load_font(title_font_key, title_font_size)
        icon_name = node.props.get("icon")
        icon_size = _scaled_value(node.props.get("icon_size"), scale, theme.get("section_icon_size", 12), 0)
        title_gap = _scaled_value(node.props.get("title_gap"), scale, theme.get("section_title_gap", 6))
        content_indent = _scaled_value(node.props.get("content_indent"), scale, theme.get("section_content_indent", 36))
        child_gap = _scaled_value(node.props.get("gap"), scale, theme.get("section_content_gap", 4))
        title_bbox = title_font.getbbox(title) if title else (0, 0, 0, 0)
        title_height = max(icon_size, title_bbox[3] - title_bbox[1])
        child_width = None if available_width is None else max(0, available_width - content_indent)
        content_height = 0
        visible_count = 0
        for child in node.children:
            _measure_component_node(child, child_width, theme, scale)
            if child.measured_height <= 0 and child.measured_width <= 0:
                continue
            if visible_count > 0:
                content_height += child_gap
            content_height += child.measured_height
            visible_count += 1
        min_height = _scaled_value(node.props.get("min_height"), scale)
        fixed_height = _scaled_value(node.props.get("height"), scale)
        fixed_width = _scaled_value(node.props.get("width"), scale)
        node.measured_width = fixed_width or available_width or max(0, content_indent + max((child.measured_width for child in node.children), default=0))
        node.measured_height = max(title_height + title_gap + content_height, min_height, fixed_height)
        node.draw_data = {
            "title": title,
            "title_font": title_font,
            "title_height": title_height,
            "title_gap": title_gap,
            "icon_name": icon_name,
            "icon_size": icon_size,
            "content_indent": content_indent,
            "child_gap": child_gap,
        }
        return
    if node.kind == "float_wrap":
        _measure_float_wrap_node(node, available_width, theme, scale)
        return
    if node.kind == "box":
        left, top, right, bottom = _component_padding(node.props, scale)
        inner_width = None if available_width is None else max(0, available_width - left - right)
        max_width = 0
        max_height = 0
        for child in node.children:
            _measure_component_node(child, inner_width, theme, scale)
            max_width = max(max_width, child.measured_width)
            max_height = max(max_height, child.measured_height)
        fixed_width = _scaled_value(node.props.get("width"), scale)
        node.measured_width = fixed_width or (available_width if available_width is not None else max_width + left + right)
        node.measured_height = max_height + top + bottom
        node.draw_data = {"padding": (left, top, right, bottom)}
        return
    node.measured_width = 0
    node.measured_height = 0
    node.draw_data = {}


def _layout_component_node(node: ComponentNode, x: int, y: int, width: int, height: int, theme: dict, scale: float) -> None:
    node.box = ComponentBox(x, y, width, height)
    if node.kind == "text":
        return
    if node.kind == "repeat":
        gap = node.draw_data.get("gap", 0)
        cursor_y = y
        for child in node.children:
            _layout_component_node(child, x, cursor_y, width, child.measured_height, theme, scale)
            cursor_y += child.measured_height + gap
        return
    if node.kind == "column":
        left, top, right, bottom = node.draw_data.get("padding", (0, 0, 0, 0))
        gap = node.draw_data.get("gap", 0)
        inner_x = x + left
        inner_y = y + top
        inner_width = max(0, width - left - right)
        inner_height = max(0, height - top - bottom)
        visible_children = [child for child in node.children if child.measured_height > 0 or child.measured_width > 0]
        if not visible_children:
            return
        gap_total = gap * max(0, len(visible_children) - 1)
        base_height = sum(child.measured_height for child in visible_children)
        extra = max(0, inner_height - base_height - gap_total)
        grow_total = sum(_component_grow(child) for child in visible_children)
        justify = node.props.get("justify", "start")
        cursor_y = inner_y
        gap_step = gap
        if grow_total <= 0:
            if justify == "center":
                cursor_y += extra // 2
            elif justify == "end":
                cursor_y += extra
            elif justify == "space_between" and len(visible_children) > 1:
                gap_step = gap + extra // (len(visible_children) - 1)
        bias_px = node.props.get("content_bias_px")
        if bias_px is not None:
            try:
                cursor_y -= int(bias_px)
            except (TypeError, ValueError):
                pass
            cursor_y = max(inner_y, cursor_y)
        for idx, child in enumerate(visible_children):
            child_height = child.measured_height
            grow = _component_grow(child)
            if grow_total > 0 and grow > 0:
                extra_height = extra if grow_total <= grow else extra * grow // grow_total
                child_height += extra_height
                extra -= extra_height
                grow_total -= grow
            _layout_component_node(child, inner_x, cursor_y, inner_width, child_height, theme, scale)
            cursor_y += child_height
            if idx < len(visible_children) - 1:
                cursor_y += gap_step
        return
    if node.kind == "row":
        left, top, right, bottom = node.draw_data.get("padding", (0, 0, 0, 0))
        gap = node.draw_data.get("gap", 0)
        inner_x = x + left
        inner_y = y + top
        inner_width = max(0, width - left - right)
        inner_height = max(0, height - top - bottom)
        fixed_width = sum(child.measured_width for child in node.children if _component_grow(child) <= 0)
        grow_children = [child for child in node.children if _component_grow(child) > 0]
        grow_total = sum(_component_grow(child) for child in grow_children)
        gap_total = gap * max(0, len(node.children) - 1)
        remaining_width = max(0, inner_width - fixed_width - gap_total)
        align = node.props.get("align", "center")
        cursor_x = inner_x
        for idx, child in enumerate(node.children):
            grow = _component_grow(child)
            child_width = child.measured_width
            if grow > 0:
                child_width = remaining_width if grow_total <= grow else remaining_width * grow // grow_total
                remaining_width -= child_width
                grow_total -= grow
            child_height = child.measured_height
            child_y = inner_y
            if align == "center":
                child_y = inner_y + max(0, (inner_height - child_height) // 2)
            elif align == "end":
                child_y = inner_y + max(0, inner_height - child_height)
            elif align == "stretch":
                child_height = inner_height
            _layout_component_node(child, cursor_x, child_y, child_width, child_height, theme, scale)
            cursor_x += child_width
            if idx < len(node.children) - 1:
                cursor_x += gap
        return
    if node.kind == "section_box":
        title_gap = node.draw_data.get("title_gap", 0)
        title_height = node.draw_data.get("title_height", 0)
        content_indent = node.draw_data.get("content_indent", 0)
        child_gap = node.draw_data.get("child_gap", 0)
        child_x = x + content_indent
        raw_coff = node.props.get("content_ink_offset_y")
        try:
            content_off = int(raw_coff) if raw_coff is not None else 0
        except (TypeError, ValueError):
            content_off = 0
        child_y = y + title_height + title_gap + content_off
        child_width = max(0, width - content_indent)
        for idx, child in enumerate([c for c in node.children if c.measured_height > 0 or c.measured_width > 0]):
            _layout_component_node(child, child_x, child_y, child_width, child.measured_height, theme, scale)
            child_y += child.measured_height
            if idx < len(node.children) - 1:
                child_y += child_gap
        return
    if node.kind == "float_wrap":
        dd = node.draw_data
        fw = int(dd.get("float_w") or 0)
        fh = int(dd.get("float_h") or 0)
        if node.children:
            _layout_component_node(node.children[0], x, y, fw, fh, theme, scale)
        return
    if node.kind == "box":
        left, top, right, bottom = node.draw_data.get("padding", (0, 0, 0, 0))
        inner_x = x + left
        inner_y = y + top
        inner_width = max(0, width - left - right)
        inner_height = max(0, height - top - bottom)
        for child in node.children:
            _layout_component_node(child, inner_x, inner_y, inner_width, min(inner_height, child.measured_height), theme, scale)
        return


def _paint_component_node(ctx: RenderContext, node: ComponentNode, theme: dict, scale: float) -> None:
    box = node.box
    if box is None:
        return
    if node.kind == "spacer":
        return
    if node.kind == "float_wrap":
        for child in node.children:
            _paint_component_node(ctx, child, theme, scale)
        dd = node.draw_data
        font = dd.get("font")
        if font is None:
            return
        lh = int(dd.get("line_height") or 0)
        if lh <= 0:
            return
        fw = int(dd.get("float_w") or 0)
        gap = int(dd.get("gap") or 0)
        fill = ctx.resolve_color(node.props)
        side_x = box.x + fw + gap
        sy = box.y
        for i, ln in enumerate(dd.get("side_lines") or []):
            ctx.draw.text((side_x, sy + i * lh), ln, fill=fill, font=font)
        below = dd.get("below_lines") or []
        if below:
            stb = int(dd.get("side_text_bottom") or 0)
            fbg = int(dd.get("float_below_gap") or 0)
            by = box.y + stb + fbg
            bx_shift = int(dd.get("below_x_shift") or 0)
            below_x = box.x + bx_shift
            for i, ln in enumerate(below):
                ctx.draw.text((below_x, by + i * lh), ln, fill=fill, font=font)
        return
    if node.kind == "text":
        font = node.draw_data.get("font")
        if font is None:
            return
        lines = node.draw_data.get("lines", [])
        line_height = node.draw_data.get("line_height", 0)
        align = node.props.get("align", "left")
        align_y = node.props.get("align_y", "top")
        total_height = node.draw_data.get("text_height", 0)
        try:
            ink_dy = int(node.props.get("ink_offset_y", 0) or 0)
        except (TypeError, ValueError):
            ink_dy = 0
        y = _component_aligned_y(box.y, box.height, total_height, align_y) + ink_dy
        for line in lines:
            bbox = font.getbbox(line)
            line_width = bbox[2] - bbox[0]
            if align == "center":
                x = box.x + max(0, (box.width - line_width) // 2)
            elif align == "right":
                x = box.x + max(0, box.width - line_width)
            else:
                x = box.x
            ctx.draw.text((x, y), line, fill=ctx.resolve_color(node.props), font=font)
            y += line_height
        return
    if node.kind == "big_number":
        font = node.draw_data.get("font")
        text = node.draw_data.get("text", "")
        if font is None or not text:
            return
        bbox = node.draw_data.get("bbox") or font.getbbox(text)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        align = node.props.get("align", "center")
        align_y = node.props.get("align_y", "top")
        if align == "left":
            x = box.x - bbox[0]
        elif align == "right":
            x = box.x + max(0, box.width - text_width) - bbox[0]
        else:
            x = box.x + max(0, (box.width - text_width) // 2) - bbox[0]
        ink_top = _component_aligned_y(box.y, box.height, text_height, align_y)
        y = ink_top - bbox[1]
        ctx.draw.text((x, y), text, fill=ctx.resolve_color(node.props), font=font)
        return
    if node.kind == "progress_bar":
        value = _num(node.content.get(node.props.get("field", ""), ""))
        max_value = max(_num(node.content.get(node.props.get("max_field", ""), "")), 1)
        ratio = max(0.0, min(1.0, value / max_value))
        width = min(box.width, node.draw_data.get("width", box.width))
        height = min(box.height, node.draw_data.get("height", box.height))
        align = node.props.get("align", "left")
        if align == "center":
            x = box.x + max(0, (box.width - width) // 2)
        elif align == "right":
            x = box.x + max(0, box.width - width)
        else:
            x = box.x
        y = box.y
        ctx.draw.rectangle([x, y, x + width, y + height], outline=EINK_FG, width=1)
        fill_w = int((width - 2) * ratio)
        if fill_w > 0:
            ctx.draw.rectangle([x + 1, y + 1, x + 1 + fill_w, y + height - 1], fill=EINK_FG)
        return
    if node.kind == "separator":
        style = node.props.get("style", "solid")
        line_width = node.draw_data.get("line_width", 1)
        margin_x = _scaled_value(node.props.get("margin_x"), scale)
        x0 = box.x + margin_x
        x1 = box.x + max(0, box.width - margin_x)
        y = box.y
        if style == "short":
            width = min(box.width, _scaled_value(node.props.get("width"), scale, 60, 4))
            x0 = box.x + max(0, (box.width - width) // 2)
            x1 = x0 + width
            ctx.draw.line([(x0, y), (x1, y)], fill=ctx.resolve_color(node.props), width=line_width)
        elif style == "dashed":
            draw_dashed_line(ctx.draw, (x0, y), (x1, y), fill=ctx.resolve_color(node.props), width=line_width)
        else:
            ctx.draw.line([(x0, y), (x1, y)], fill=ctx.resolve_color(node.props), width=line_width)
        return
    if node.kind == "section_box":
        title = node.draw_data.get("title", "")
        title_font = node.draw_data.get("title_font")
        title_height = node.draw_data.get("title_height", 0)
        icon_name = node.draw_data.get("icon_name")
        icon_size = node.draw_data.get("icon_size", 0)
        title_x = box.x
        if icon_name:
            icon_img = load_icon(icon_name, size=(icon_size, icon_size))
            if icon_img:
                ctx.paste_icon(icon_img, (title_x, box.y))
                title_x += _scaled_value(theme.get("section_icon_gap"), scale, 16)
        if title and title_font is not None:
            title_y = box.y + max(0, (title_height - (title_font.getbbox(title)[3] - title_font.getbbox(title)[1])) // 2)
            ctx.draw.text((title_x, title_y), title, fill=ctx.resolve_color(node.props), font=title_font)
    for child in node.children:
        _paint_component_node(ctx, child, theme, scale)
    if node.props.get("border") and box.width > 0 and box.height > 0:
        bw = _scaled_value(node.props.get("border_width"), scale, 1, 1)
        ctx.draw.rectangle(
            [box.x, box.y, box.x + box.width - 1, box.y + box.height - 1],
            outline=EINK_FG, width=bw,
        )


def _render_component_tree_mode(
    draw: ImageDraw.ImageDraw,
    img: Image.Image,
    content: dict,
    body_tree: dict,
    theme: dict,
    *,
    screen_w: int,
    screen_h: int,
    status_bar_bottom: int,
    footer_height: int,
    footer_top_offset: int = 0,
    colors: int,
) -> RenderContext:
    ctx = RenderContext(
        draw=draw,
        img=img,
        content=content,
        screen_w=screen_w,
        screen_h=screen_h,
        y=status_bar_bottom,
        footer_height=footer_height,
        footer_top_offset=footer_top_offset,
        colors=colors,
    )
    scale = _component_tree_scale(ctx, theme)
    root = _build_component_node(body_tree, content)
    available_height = max(0, ctx.footer_top - status_bar_bottom)
    _measure_component_node(root, screen_w, theme, scale)
    root_height = available_height if root.kind == "column" else min(available_height, root.measured_height)
    _layout_component_node(root, 0, status_bar_bottom, screen_w, root_height, theme, scale)
    _paint_component_node(ctx, root, theme, scale)
    debug_overlay = body_tree.get("debug_overlay")
    if debug_overlay is None:
        debug_overlay = theme.get("debug_overlay")
    if debug_overlay:
        _paint_component_debug_overlay(ctx, root)
    return ctx


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
                _render_block(measure_ctx, block)
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
                _render_block(ctx, block)
        else:
            ctx = RenderContext(
                draw=draw, img=img, content=content,
                screen_w=screen_w, screen_h=screen_h,
                y=status_bar_bottom, footer_height=footer_height, footer_top_offset=footer_top_offset, colors=colors,
            )
            for block in body:
                if ctx.y >= footer_top - 10:
                    break
                _render_block(ctx, block)

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
