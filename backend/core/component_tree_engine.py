"""
墨水屏声明式组件树渲染引擎 (E-Ink Component Tree Layout & Paint Engine)
下沉抽取的完整现代组件树（Flex, Grid, Float-wrap, Repeat, Box-model, Debug Overlay 等）。
"""
from __future__ import annotations

import logging
import math
import os
import re
from dataclasses import dataclass, field
from typing import Any
from PIL import Image, ImageDraw

from core.patterns.utils import (
    EINK_BG,
    EINK_FG,
    has_cjk,
    load_font,
    load_font_by_name,
    load_icon,
    draw_dashed_line,
    wrap_text,
    safe_font_bbox,
)
from core.blocks.context import RenderContext, resolve_template as _resolve_template
from core.blocks.text import pick_cjk_font as _pick_cjk_font

logger = logging.getLogger(__name__)

_LARGE_PANEL_MIN_W = int(os.getenv("INKSIGHT_LARGE_PANEL_MIN_WIDTH", "648"))


def _num(v: Any) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0

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


def _measure_component_ring_progress(node: ComponentNode, scale: float) -> None:
    size = _scaled_value(node.props.get("size", 48), scale, 48, 16)
    node.measured_width = size
    node.measured_height = size
    node.draw_data = {"size": size}


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
    raw_children = defn.get("children", [])
    if not raw_children and "items" in defn and isinstance(defn.get("items"), list):
        raw_children = defn.get("items", [])
    children = [
        _build_component_node(child, content)
        for child in raw_children
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
    if node.kind == "ring_progress":
        _measure_component_ring_progress(node, scale)
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
    if node.kind == "ring_progress":
        value = _num(node.content.get(node.props.get("field", ""), ""))
        max_value = max(_num(node.content.get(node.props.get("max_field", ""), "")), 1)
        ratio = max(0.0, min(1.0, value / max_value))
        size = min(box.width, box.height, node.draw_data.get("size", min(box.width, box.height)))
        x = box.x + max(0, (box.width - size) // 2)
        y = box.y + max(0, (box.height - size) // 2)

        cx = x + size // 2
        cy = y + size // 2
        r = (size - 4) // 2
        ring_w = max(2, _scaled_value(node.props.get("ring_width", 3), scale, 3, 1))

        # 绘制背景底轨 (浅灰色细线)
        color = ctx.resolve_color(node.props)
        track_color = 180 if ctx.colors > 2 else color
        ctx.draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=track_color, width=1)
        ctx.draw.ellipse([cx - r + ring_w, cy - r + ring_w, cx + r - ring_w, cy + r - ring_w], outline=track_color, width=1)

        # 绘制进度弧段 (从 12 点钟方向 -90 度开始顺时针)
        if ratio > 0.01:
            end_deg = -90 + int(360.0 * ratio)
            for dr in range(ring_w):
                ctx.draw.arc([cx - r + dr, cy - r + dr, cx + r - dr, cy + r - dr], start=-90, end=end_deg, fill=color, width=1)

        # 绘制环形中间的文本 (如 85%)
        center_text = str(node.content.get(node.props.get("text_field", ""), ""))
        if not center_text:
            center_text = f"{int(ratio * 100)}%"
        
        font_size = _scaled_value(node.props.get("font_size", 10), scale, 10, 7)
        font_name = node.props.get("font", "roboto_bold")
        font = load_font(font_name, font_size)
        bbox = font.getbbox(center_text)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        tx = cx - tw // 2
        ty = cy - th // 2 - bbox[1]
        ctx.draw.text((tx, ty), center_text, fill=color, font=font)
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

