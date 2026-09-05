"""
极客与高密度排版组件扩展模块 (Geek Widgets & Dense Layout Blocks)
提供高度契合墨水屏的专业排版组件：
1. stat_progress_bar: 双端统计进度条（带标签、比例填充、数值与百分比）
2. pill_tag_list: 自适应流式胶囊标签组（自动折行、胶囊边框、实心与空心）
3. code_snippet_box: 极客终端代码卡片（带控制台三圆点顶栏、等宽文本排版）
【规范约束】：严格禁止 Emoji。
"""
from __future__ import annotations

import logging
from typing import Any
from PIL import ImageDraw

from core.patterns.utils import (
    EINK_BG,
    EINK_FG,
    EINK_COLOR_NAME_MAP,
    load_font,
    safe_font_bbox,
    wrap_text,
)
from .context import RenderContext
from .registry import register_block

logger = logging.getLogger(__name__)

_RED_COLOR = EINK_COLOR_NAME_MAP.get("red", 3 if 3 in EINK_COLOR_NAME_MAP.values() else 2)


def _draw_rounded_rect(draw: ImageDraw.ImageDraw, bbox: tuple[int, int, int, int], radius: int, fill=None, outline=None, width: int = 1):
    try:
        draw.rounded_rectangle(bbox, radius=radius, fill=fill, outline=outline, width=width)
    except AttributeError:
        draw.rectangle(bbox, fill=fill, outline=outline, width=width)


def render_stat_progress_bar(ctx: RenderContext, block: dict[str, Any]) -> None:
    """渲染带统计数值与双端标签的精细进度条。"""
    label = str(block.get("label") or ctx.resolve(block.get("label_template", "")))
    val = float(block.get("value") or ctx.get_field(block.get("value_field", "")) or 0.0)
    max_val = float(block.get("max_value", 100.0) or 100.0)
    unit = str(block.get("unit") or "")
    show_pct = bool(block.get("show_percent", True))

    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    bar_h = max(4, int(block.get("height", 7) * ctx.scale))
    margin_bottom = int(block.get("margin_bottom", 6) * ctx.scale)

    x1 = ctx.x_offset + margin_x
    x2 = ctx.x_offset + ctx.available_width - margin_x
    avail_w = max(20, x2 - x1)

    pct = max(0.0, min(100.0, (val / max_val * 100.0) if max_val > 0 else 0.0))

    # 1. 绘制顶端信息行 (Label ... 78.5% 12/16GB)
    font_size = int(block.get("font_size", 11) * ctx.scale)
    label_font = load_font("noto_serif_bold", font_size)
    num_font = load_font("noto_serif_regular", font_size)

    stat_parts = []
    if show_pct:
        stat_parts.append(f"{pct:.1f}%")
    if unit:
        stat_parts.append(f"{val:.1f}/{max_val:.1f} {unit}")
    stat_str = " · ".join(stat_parts)

    y1 = ctx.y
    if label:
        ctx.draw.text((x1, y1), label, fill=EINK_FG, font=label_font)
    if stat_str:
        num_bbox = safe_font_bbox(num_font, stat_str)
        num_w = num_bbox[2] - num_bbox[0]
        ctx.draw.text((x2 - num_w, y1), stat_str, fill=EINK_FG, font=num_font)

    text_h = font_size + 4
    by1 = y1 + text_h + 3
    by2 = by1 + bar_h

    # 2. 绘制进度条槽底 (槽外框)
    _draw_rounded_rect(ctx.draw, (x1, by1, x2, by2), radius=bar_h // 2, outline=EINK_FG, width=1)

    # 3. 填充已完成进度
    fill_w = int(avail_w * (pct / 100.0))
    if fill_w > 2:
        fill_color = EINK_FG
        cname = block.get("color", "")
        if cname == "red" and ctx.colors >= 3:
            fill_color = _RED_COLOR
        _draw_rounded_rect(ctx.draw, (x1 + 1, by1 + 1, x1 + fill_w - 1, by2 - 1), radius=max(1, bar_h // 2 - 1), fill=fill_color)

    ctx.y = by2 + margin_bottom


def render_pill_tag_list(ctx: RenderContext, block: dict[str, Any]) -> None:
    """渲染自适应折行的流式胶囊标签组 (Pill Tag Cloud)。"""
    items = block.get("items")
    if items is None:
        items = ctx.get_field(block.get("field", "")) or []
    if not isinstance(items, list) or not items:
        return

    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 6) * ctx.scale)
    gap_x = int(block.get("gap_x", 6) * ctx.scale)
    gap_y = int(block.get("gap_y", 5) * ctx.scale)
    variant = block.get("variant", "outline")  # outline / solid / soft

    font_size = int(block.get("font_size", 10) * ctx.scale)
    font = load_font("noto_serif_regular", font_size)

    pad_x = int(block.get("padding_x", 6) * ctx.scale)
    pad_y = int(block.get("padding_y", 2) * ctx.scale)
    tag_h = font_size + pad_y * 2 + 2

    x_start = ctx.x_offset + margin_x
    max_x = ctx.x_offset + ctx.available_width - margin_x

    cur_x = x_start
    cur_y = ctx.y

    for item in items:
        text = str(item).strip()
        if not text:
            continue
        tb = safe_font_bbox(font, text)
        tw = tb[2] - tb[0]
        pill_w = tw + pad_x * 2

        # 换行检测
        if cur_x + pill_w > max_x and cur_x > x_start:
            cur_x = x_start
            cur_y += tag_h + gap_y

        pill_box = (cur_x, cur_y, cur_x + pill_w, cur_y + tag_h)
        radius = tag_h // 2

        if variant == "solid":
            _draw_rounded_rect(ctx.draw, pill_box, radius=radius, fill=EINK_FG)
            ctx.draw.text((cur_x + pad_x, cur_y + pad_y), text, fill=EINK_BG, font=font)
        else:
            _draw_rounded_rect(ctx.draw, pill_box, radius=radius, outline=EINK_FG, width=1)
            ctx.draw.text((cur_x + pad_x, cur_y + pad_y), text, fill=EINK_FG, font=font)

        cur_x += pill_w + gap_x

    ctx.y = cur_y + tag_h + margin_bottom


def render_code_snippet_box(ctx: RenderContext, block: dict[str, Any]) -> None:
    """渲染极客风格的终端代码/配置卡片。"""
    title = str(block.get("title") or ctx.resolve(block.get("title_template", "terminal")))
    code_raw = block.get("code") or block.get("lines")
    if code_raw is None:
        code_raw = ctx.get_field(block.get("field", "")) or []

    if isinstance(code_raw, str):
        lines = code_raw.splitlines()
    elif isinstance(code_raw, list):
        lines = [str(line) for line in code_raw]
    else:
        lines = []

    lines = lines[:6] or ["# No output"]

    margin_x = int(block.get("margin_x", 12) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 6) * ctx.scale)

    x1 = ctx.x_offset + margin_x
    x2 = ctx.x_offset + ctx.available_width - margin_x
    box_w = x2 - x1

    title_bar_h = int(18 * ctx.scale)
    code_font_size = int(block.get("font_size", 10) * ctx.scale)
    code_font = load_font("noto_serif_regular", code_font_size)
    title_font = load_font("noto_serif_bold", int(9 * ctx.scale))

    line_h = code_font_size + 4
    content_h = len(lines) * line_h + 8
    total_h = title_bar_h + content_h

    y1 = ctx.y
    y2 = y1 + total_h

    # 1. 绘制终端外框
    _draw_rounded_rect(ctx.draw, (x1, y1, x2, y2), radius=4, outline=EINK_FG, width=1)

    # 2. 绘制顶栏分割线与背景
    ctx.draw.rectangle((x1, y1, x2, y1 + title_bar_h), fill=EINK_FG)

    # 3. 绘制三个控制台小圆点
    dot_r = max(2, int(2.5 * ctx.scale))
    for i in range(3):
        dx = x1 + 8 + i * (dot_r * 2 + 4)
        dy = y1 + title_bar_h // 2
        ctx.draw.ellipse((dx - dot_r, dy - dot_r, dx + dot_r, dy + dot_r), fill=EINK_BG)

    # 顶栏标题
    tb = safe_font_bbox(title_font, title)
    tw = tb[2] - tb[0]
    ctx.draw.text((x2 - tw - 8, y1 + (title_bar_h - 9) // 2), title, fill=EINK_BG, font=title_font)

    # 4. 绘制代码内容
    cur_y = y1 + title_bar_h + 4
    for line in lines:
        wrapped = wrap_text(line, code_font, box_w - 16)[:1]
        line_text = wrapped[0] if wrapped else line
        ctx.draw.text((x1 + 8, cur_y), line_text, fill=EINK_FG, font=code_font)
        cur_y += line_h

    ctx.y = y2 + margin_bottom


# 注册组件
register_block("stat_progress_bar", render_stat_progress_bar)
register_block("pill_tag_list", render_pill_tag_list)
register_block("code_snippet_box", render_code_snippet_box)
