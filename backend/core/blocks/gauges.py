"""
仪表盘与环形量表组件模块 (Gauges, Progress Rings & KPI Differentials)
包含：gauge (半圆仪表盘), progress_ring (环形进度量表), kpi_diff (趋势对比指标)
"""
from __future__ import annotations

import math
import logging
from typing import Any

from core.patterns.utils import (
    EINK_BG,
    EINK_FG,
    has_cjk,
    load_font,
)
from .context import RenderContext
from .registry import register_block
from .text import pick_cjk_font

logger = logging.getLogger(__name__)


def _num(v: Any) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def render_gauge(ctx: RenderContext, block: dict) -> None:
    """渲染 180 度墨水屏半圆仪表盘（带刻度基线、指针或进度弧与中央读数）。"""
    scale = ctx.scale
    val = _num(ctx.get_field(block.get("field", "")) if block.get("field") else block.get("value", 0))
    min_val = _num(block.get("min", 0))
    max_val = _num(block.get("max", 100))
    unit = str(block.get("unit", ""))
    title = str(block.get("title", ""))

    span = max_val - min_val if max_val > min_val else 1.0
    ratio = max(0.0, min(1.0, (val - min_val) / span))

    size = int(block.get("size", 100) * scale)
    radius = size // 2
    margin_x = int(block.get("margin_x", 0) * scale)
    margin_bottom = int(block.get("margin_bottom", 8) * scale)

    center_x = ctx.x_offset + (ctx.available_width - size) // 2 + radius
    center_y = ctx.y + radius

    # 1. 绘制背景圆弧 (180 度半圆，从 180° 到 360°)
    box = [center_x - radius, center_y - radius, center_x + radius, center_y + radius]
    ctx.draw.arc(box, start=180, end=0, fill=EINK_FG, width=max(1, int(2 * scale)))

    # 2. 绘制基线网点阴影/进度弧
    active_angle = 180 + int(ratio * 180)
    arc_color = ctx.color_index(block.get("color", "red" if ctx.colors >= 3 else "black"), default=EINK_FG)
    ctx.draw.arc(box, start=180, end=active_angle, fill=arc_color, width=max(2, int(4 * scale)))

    # 3. 绘制指针指示线
    rad = math.radians(active_angle)
    pointer_len = radius - int(8 * scale)
    px = center_x + pointer_len * math.cos(rad)
    py = center_y + pointer_len * math.sin(rad)
    ctx.draw.line([(center_x, center_y), (px, py)], fill=EINK_FG, width=max(1, int(2 * scale)))

    # 轴心小圆
    r_core = max(2, int(3 * scale))
    ctx.draw.ellipse([center_x - r_core, center_y - r_core, center_x + r_core, center_y + r_core], fill=EINK_FG)

    # 4. 读数文字
    font_val = load_font("noto_serif_bold", int(14 * scale))
    font_lbl = load_font("noto_serif_light", int(9 * scale))

    val_str = f"{val:g}{unit}"
    vbox = font_val.getbbox(val_str)
    vw = vbox[2] - vbox[0]
    ctx.draw.text((center_x - vw // 2, center_y + int(4 * scale)), val_str, fill=EINK_FG, font=font_val)

    if title:
        tbox = font_lbl.getbbox(title)
        tw = tbox[2] - tbox[0]
        ctx.draw.text((center_x - tw // 2, ctx.y - int(2 * scale)), title, fill=EINK_FG, font=font_lbl)

    # 端点刻度标注 (min / max)
    min_str = f"{min_val:g}"
    max_str = f"{max_val:g}"
    ctx.draw.text((center_x - radius, center_y + int(2 * scale)), min_str, fill=EINK_FG, font=font_lbl)
    mbox = font_lbl.getbbox(max_str)
    ctx.draw.text((center_x + radius - (mbox[2] - mbox[0]), center_y + int(2 * scale)), max_str, fill=EINK_FG, font=font_lbl)

    ctx.y = center_y + int(20 * scale) + margin_bottom


def render_progress_ring(ctx: RenderContext, block: dict) -> None:
    """渲染 360 度紧凑环形百分比量表。"""
    scale = ctx.scale
    pct = _num(ctx.get_field(block.get("field", "")) if block.get("field") else block.get("percent", 50))
    pct = max(0.0, min(100.0, pct))
    ratio = pct / 100.0

    size = int(block.get("size", 64) * scale)
    radius = size // 2
    margin_bottom = int(block.get("margin_bottom", 6) * scale)
    center_x = ctx.x_offset + (ctx.available_width - size) // 2 + radius
    center_y = ctx.y + radius

    box = [center_x - radius, center_y - radius, center_x + radius, center_y + radius]
    # 背景浅轮廓
    ctx.draw.arc(box, start=0, end=360, fill=EINK_FG, width=1)

    # 有效进度弧 (从 -90° 开始顺时针走)
    if ratio > 0:
        active_color = ctx.color_index(block.get("color", "red" if ctx.colors >= 3 else "black"), default=EINK_FG)
        end_deg = -90 + int(ratio * 360)
        ctx.draw.arc(box, start=-90, end=end_deg, fill=active_color, width=max(2, int(4 * scale)))

    # 中央百分比文本
    font = load_font("noto_serif_bold", int(12 * scale))
    pct_text = f"{int(round(pct))}%"
    pbox = font.getbbox(pct_text)
    pw = pbox[2] - pbox[0]
    ph = pbox[3] - pbox[1]
    ctx.draw.text((center_x - pw // 2, center_y - ph // 2 - pbox[1]), pct_text, fill=EINK_FG, font=font)

    label = str(block.get("label", ""))
    if label:
        font_lbl = load_font("noto_serif_light", int(9 * scale))
        lbox = font_lbl.getbbox(label)
        lw = lbox[2] - lbox[0]
        ctx.draw.text((center_x - lw // 2, center_y + radius + int(2 * scale)), label, fill=EINK_FG, font=font_lbl)
        ctx.y = center_y + radius + int(14 * scale) + margin_bottom
    else:
        ctx.y = center_y + radius + margin_bottom


def render_kpi_diff(ctx: RenderContext, block: dict) -> None:
    """渲染带差值对比与趋势箭头的 KPI 指标组件。"""
    scale = ctx.scale
    title = str(ctx.get_field(block.get("title_field", "")) if block.get("title_field") else block.get("title", ""))
    val = str(ctx.get_field(block.get("field", "")) if block.get("field") else block.get("value", ""))
    diff = str(ctx.get_field(block.get("diff_field", "")) if block.get("diff_field") else block.get("diff", ""))
    trend = str(block.get("trend", "up" if "+" in diff else ("down" if "-" in diff else "flat")))

    margin_x = int(block.get("margin_x", 12) * scale)
    margin_bottom = int(block.get("margin_bottom", 6) * scale)
    align = block.get("align", "left")

    font_title = load_font("noto_serif_light", int(11 * scale))
    font_val = load_font("noto_serif_bold", int(20 * scale))
    font_diff = load_font("noto_serif_regular", int(11 * scale))

    vbox = font_val.getbbox(val)
    vw = vbox[2] - vbox[0]
    vh = vbox[3] - vbox[1]

    arrow = "▲ " if trend == "up" else ("▼ " if trend == "down" else "• ")
    diff_text = f"{arrow}{diff}" if diff else ""
    diff_box = font_diff.getbbox(diff_text) if diff_text else (0, 0, 0, 0)
    dw = diff_box[2] - diff_box[0]

    pad_pill = int(4 * scale)
    total_w = vw + (dw + pad_pill * 2 + int(6 * scale) if diff_text else 0)

    if align == "center":
        start_x = ctx.x_offset + (ctx.available_width - total_w) // 2
    elif align == "right":
        start_x = ctx.x_offset + ctx.available_width - margin_x - total_w
    else:
        start_x = ctx.x_offset + margin_x

    cur_y = ctx.y
    if title:
        ctx.draw.text((start_x, cur_y), title, fill=EINK_FG, font=font_title)
        cur_y += int(14 * scale)

    # 绘制主要数值
    val_color = ctx.color_index(block.get("color", "black"), default=EINK_FG)
    ctx.draw.text((start_x, cur_y), val, fill=val_color, font=font_val)

    # 绘制右侧差异指示胶囊
    if diff_text:
        diff_color_name = "red" if (trend == "up" and ctx.colors >= 3) else ("black" if trend != "down" else "black")
        diff_fill = ctx.color_index(diff_color_name, default=EINK_FG)

        pill_x = start_x + vw + int(6 * scale)
        pill_y = cur_y + (vh - (diff_box[3] - diff_box[1])) // 2
        pill_w = dw + pad_pill * 2
        pill_h = (diff_box[3] - diff_box[1]) + pad_pill * 2

        ctx.draw.rounded_rectangle([pill_x, pill_y, pill_x + pill_w, pill_y + pill_h], radius=3, outline=diff_fill, width=1)
        ctx.draw.text((pill_x + pad_pill, pill_y + pad_pill - diff_box[1]), diff_text, fill=diff_fill, font=font_diff)

    ctx.y = cur_y + vh + margin_bottom


# 注册所有量表与指标对比类组件
register_block("gauge", render_gauge)
register_block("progress_ring", render_progress_ring)
register_block("kpi_diff", render_kpi_diff)
