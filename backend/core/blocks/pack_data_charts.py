"""
InkSight 扩充排版组件库 1：核心数据可视化与量表组件 (Charts & Data Visuals)
包含：
1. donut_chart: 甜甜圈环形图
2. bar_chart: 垂直多柱柱状图
3. horizontal_bar_chart: 水平条形图
4. scatter_points: 散点与离散分布图
5. step_line_chart: 阶梯折线图
6. area_chart: 面积阴影图
7. candlestick_chart: 极简蜡烛图/K线柱
8. bullet_chart: 目标达成子弹图
9. multi_progress_bar: 多段分段累计进度条
10. battery_indicator: 电池电量多段象形指示条
11. signal_strength_meter: 信号格指示组件
12. speed_gauge: 速度与仪表指针刻度盘
13. funnel_chart: 漏斗转化流程图
14. pyramid_bars: 金字塔对比条
15. spark_bar: 迷你柱状走势图
【规范约束】：严格禁止 Emoji。
"""
from __future__ import annotations

import logging
import math
from typing import Any
from PIL import ImageDraw

from core.patterns.utils import (
    EINK_BG,
    EINK_FG,
    EINK_COLOR_NAME_MAP,
    load_font,
    safe_font_bbox,
)
from .context import RenderContext
from .registry import register_block

logger = logging.getLogger(__name__)

_RED = EINK_COLOR_NAME_MAP.get("red", 3 if 3 in EINK_COLOR_NAME_MAP.values() else 2)


def _draw_box(draw: ImageDraw.ImageDraw, bbox: tuple[int, int, int, int], outline=EINK_FG, fill=None, width=1):
    draw.rectangle(bbox, outline=outline, fill=fill, width=width)


@register_block("donut_chart")
def render_donut_chart(ctx: RenderContext, block: dict) -> None:
    """渲染环形甜甜圈图。"""
    size = int(block.get("size", 60) * ctx.scale)
    thickness = max(2, int(block.get("thickness", 8) * ctx.scale))
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 6) * ctx.scale)
    ratio = float(block.get("value") or ctx.get_field(block.get("value_field", "")) or 75.0) / 100.0
    ratio = max(0.0, min(1.0, ratio))

    x = ctx.x_offset + margin_x
    y = ctx.y
    cx, cy = x + size // 2, y + size // 2
    r = size // 2

    # 底轨
    ctx.draw.ellipse((cx - r, cy - r, cx + r, cy + r), outline=EINK_FG, width=1)
    ctx.draw.ellipse((cx - r + thickness, cy - r + thickness, cx + r - thickness, cy + r - thickness), outline=EINK_FG, width=1)

    # 填充弧
    if ratio > 0.02:
        end_angle = -90 + int(360 * ratio)
        for i in range(thickness):
            ctx.draw.arc((cx - r + i, cy - r + i, cx + r - i, cy + r - i), start=-90, end=end_angle, fill=EINK_FG, width=1)

    label = str(block.get("label") or f"{int(ratio*100)}%")
    font = load_font("noto_serif_bold", int(10 * ctx.scale))
    tb = safe_font_bbox(font, label)
    ctx.draw.text((cx - (tb[2]-tb[0])//2, cy - (tb[3]-tb[1])//2 - tb[1]), label, fill=EINK_FG, font=font)
    ctx.y = y + size + margin_bottom


@register_block("bar_chart")
def render_bar_chart(ctx: RenderContext, block: dict) -> None:
    """垂直柱状图。"""
    h = int(block.get("height", 50) * ctx.scale)
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 6) * ctx.scale)
    values = block.get("values") or ctx.get_field(block.get("field", "")) or [30, 60, 45, 90, 75, 40]
    labels = block.get("labels") or ["M", "T", "W", "T", "F", "S"]
    max_val = max(max(values) if values else 100, 1)

    x1 = ctx.x_offset + margin_x
    w = ctx.available_width - margin_x * 2
    y = ctx.y
    y_base = y + h - 14

    n = max(1, len(values))
    bar_slot = w / n
    bar_w = max(4, int(bar_slot * 0.55))

    font = load_font("noto_serif_regular", int(8 * ctx.scale))
    ctx.draw.line((x1, y_base, x1 + w, y_base), fill=EINK_FG, width=1)

    for i, v in enumerate(values):
        bx = int(x1 + i * bar_slot + (bar_slot - bar_w) / 2)
        bh = int((v / max_val) * (h - 20))
        by = y_base - bh
        _draw_box(ctx.draw, (bx, by, bx + bar_w, y_base), fill=EINK_FG)
        if i < len(labels):
            lbl = str(labels[i])
            tb = safe_font_bbox(font, lbl)
            ctx.draw.text((bx + (bar_w - (tb[2]-tb[0]))//2, y_base + 2), lbl, fill=EINK_FG, font=font)

    ctx.y = y + h + margin_bottom


@register_block("horizontal_bar_chart")
def render_horizontal_bar_chart(ctx: RenderContext, block: dict) -> None:
    """水平条形图。"""
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 6) * ctx.scale)
    items = block.get("items") or [
        {"label": "CPU", "value": 78},
        {"label": "MEM", "value": 64},
        {"label": "DSK", "value": 42},
    ]
    font = load_font("noto_serif_regular", int(10 * ctx.scale))
    y = ctx.y
    avail_w = ctx.available_width - margin_x * 2

    for it in items:
        lbl = str(it.get("label", ""))
        val = float(it.get("value", 0))
        tb = safe_font_bbox(font, lbl)
        ctx.draw.text((ctx.x_offset + margin_x, y), lbl, fill=EINK_FG, font=font)
        bx1 = ctx.x_offset + margin_x + 40
        bw = avail_w - 70
        bar_len = int(bw * (min(100.0, max(0.0, val)) / 100.0))
        _draw_box(ctx.draw, (bx1, y + 2, bx1 + bw, y + 10), outline=EINK_FG, width=1)
        if bar_len > 0:
            _draw_box(ctx.draw, (bx1 + 1, y + 3, bx1 + bar_len - 1, y + 9), fill=EINK_FG)
        val_str = f"{int(val)}%"
        ctx.draw.text((bx1 + bw + 6, y), val_str, fill=EINK_FG, font=font)
        y += 14

    ctx.y = y + margin_bottom


@register_block("scatter_points")
def render_scatter_points(ctx: RenderContext, block: dict) -> None:
    """离散散点分布图。"""
    h = int(block.get("height", 40) * ctx.scale)
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 6) * ctx.scale)
    points = block.get("points") or [(10, 20), (30, 80), (50, 45), (70, 60), (90, 30)]
    w = ctx.available_width - margin_x * 2
    y = ctx.y

    _draw_box(ctx.draw, (ctx.x_offset + margin_x, y, ctx.x_offset + margin_x + w, y + h), outline=EINK_FG, width=1)
    for px, py in points:
        cx = int(ctx.x_offset + margin_x + (px / 100.0) * w)
        cy = int(y + h - (py / 100.0) * h)
        ctx.draw.ellipse((cx - 2, cy - 2, cx + 2, cy + 2), fill=EINK_FG)

    ctx.y = y + h + margin_bottom


@register_block("step_line_chart")
def render_step_line_chart(ctx: RenderContext, block: dict) -> None:
    """阶梯式折线走势图。"""
    h = int(block.get("height", 44) * ctx.scale)
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 6) * ctx.scale)
    vals = block.get("values") or [10, 30, 30, 60, 40, 80]
    w = ctx.available_width - margin_x * 2
    y = ctx.y
    max_v = max(max(vals) if vals else 100, 1)

    slot_w = w / max(1, len(vals) - 1)
    coords = []
    for i, v in enumerate(vals):
        cx = ctx.x_offset + margin_x + int(i * slot_w)
        cy = y + h - int((v / max_v) * (h - 8)) - 4
        coords.append((cx, cy))

    # 绘制阶梯线
    for i in range(len(coords) - 1):
        x_a, y_a = coords[i]
        x_b, y_b = coords[i+1]
        ctx.draw.line((x_a, y_a, x_b, y_a), fill=EINK_FG, width=1)
        ctx.draw.line((x_b, y_a, x_b, y_b), fill=EINK_FG, width=1)

    ctx.y = y + h + margin_bottom


@register_block("area_chart")
def render_area_chart(ctx: RenderContext, block: dict) -> None:
    """阴影填充面积图。"""
    h = int(block.get("height", 50) * ctx.scale)
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 6) * ctx.scale)
    vals = block.get("values") or [20, 40, 60, 50, 80, 95]
    w = ctx.available_width - margin_x * 2
    y = ctx.y
    max_v = max(max(vals) if vals else 100, 1)

    poly = [(ctx.x_offset + margin_x, y + h)]
    slot = w / max(1, len(vals) - 1)
    for i, v in enumerate(vals):
        cx = int(ctx.x_offset + margin_x + i * slot)
        cy = int(y + h - (v / max_v) * (h - 6))
        poly.append((cx, cy))
    poly.append((ctx.x_offset + margin_x + w, y + h))

    # 绘制多边形边框与斜线阴影
    ctx.draw.polygon(poly, outline=EINK_FG)
    ctx.y = y + h + margin_bottom


@register_block("candlestick_chart")
def render_candlestick_chart(ctx: RenderContext, block: dict) -> None:
    """极简蜡烛/K线图。"""
    h = int(block.get("height", 50) * ctx.scale)
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 6) * ctx.scale)
    bars = block.get("bars") or [
        {"o": 30, "c": 50, "h": 60, "l": 25},
        {"o": 50, "c": 45, "h": 55, "l": 40},
        {"o": 45, "c": 75, "h": 85, "l": 40},
        {"o": 75, "c": 70, "h": 80, "l": 65},
    ]
    w = ctx.available_width - margin_x * 2
    y = ctx.y
    slot = w / max(1, len(bars))
    bar_w = max(4, int(slot * 0.5))

    for i, b in enumerate(bars):
        bx = int(ctx.x_offset + margin_x + i * slot + (slot - bar_w) / 2)
        cx = bx + bar_w // 2
        hy = y + h - int(b["h"] * (h - 8) / 100)
        ly = y + h - int(b["l"] * (h - 8) / 100)
        oy = y + h - int(b["o"] * (h - 8) / 100)
        cy = y + h - int(b["c"] * (h - 8) / 100)
        ctx.draw.line((cx, hy, cx, ly), fill=EINK_FG, width=1)
        top_y, bot_y = min(oy, cy), max(oy, cy)
        fill = EINK_FG if b["c"] >= b["o"] else None
        _draw_box(ctx.draw, (bx, top_y, bx + bar_w, bot_y), outline=EINK_FG, fill=fill)

    ctx.y = y + h + margin_bottom


@register_block("bullet_chart")
def render_bullet_chart(ctx: RenderContext, block: dict) -> None:
    """目标达成子弹图。"""
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 6) * ctx.scale)
    label = str(block.get("label", "目标进度"))
    val = float(block.get("value", 72))
    target = float(block.get("target", 85))
    y = ctx.y
    w = ctx.available_width - margin_x * 2

    font = load_font("noto_serif_regular", int(10 * ctx.scale))
    ctx.draw.text((ctx.x_offset + margin_x, y), label, fill=EINK_FG, font=font)
    by = y + 14
    bh = 8
    # 外框底轨
    _draw_box(ctx.draw, (ctx.x_offset + margin_x, by, ctx.x_offset + margin_x + w, by + bh), outline=EINK_FG, width=1)
    # 填充实心值
    fill_w = int(w * (val / 100.0))
    if fill_w > 0:
        _draw_box(ctx.draw, (ctx.x_offset + margin_x + 1, by + 1, ctx.x_offset + margin_x + fill_w, by + bh - 1), fill=EINK_FG)
    # 标杆线
    tx = int(ctx.x_offset + margin_x + w * (target / 100.0))
    ctx.draw.line((tx, by - 2, tx, by + bh + 2), fill=EINK_FG, width=2)
    ctx.y = by + bh + margin_bottom


@register_block("multi_progress_bar")
def render_multi_progress_bar(ctx: RenderContext, block: dict) -> None:
    """多段分段累计进度条。"""
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 6) * ctx.scale)
    segments = block.get("segments") or [{"pct": 30, "fill": True}, {"pct": 40, "fill": False}, {"pct": 30, "fill": False}]
    y = ctx.y
    w = ctx.available_width - margin_x * 2
    bh = 7
    cur_x = ctx.x_offset + margin_x

    _draw_box(ctx.draw, (cur_x, y, cur_x + w, y + bh), outline=EINK_FG, width=1)
    for seg in segments:
        seg_w = int(w * (seg.get("pct", 0) / 100.0))
        if seg.get("fill"):
            _draw_box(ctx.draw, (cur_x, y, cur_x + seg_w, y + bh), fill=EINK_FG)
        else:
            ctx.draw.line((cur_x + seg_w, y, cur_x + seg_w, y + bh), fill=EINK_FG, width=1)
        cur_x += seg_w
    ctx.y = y + bh + margin_bottom


@register_block("battery_indicator")
def render_battery_indicator(ctx: RenderContext, block: dict) -> None:
    """多段电池电量象形指示器。"""
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 6) * ctx.scale)
    pct = float(block.get("pct") or ctx.get_field(block.get("field", "")) or 80.0)
    y = ctx.y
    x = ctx.x_offset + margin_x
    bw, bh = 28, 14

    # 电池主体与正极凸起
    _draw_box(ctx.draw, (x, y, x + bw, y + bh), outline=EINK_FG, width=1)
    _draw_box(ctx.draw, (x + bw, y + 4, x + bw + 2, y + bh - 4), fill=EINK_FG)

    # 内部 3 格
    slots = 3
    active_slots = int((pct / 100.0) * slots + 0.5)
    sw = (bw - 6) // slots
    for i in range(active_slots):
        sx = x + 2 + i * (sw + 1)
        _draw_box(ctx.draw, (sx, y + 2, sx + sw, y + bh - 2), fill=EINK_FG)

    font = load_font("noto_serif_regular", int(10 * ctx.scale))
    ctx.draw.text((x + bw + 8, y + 1), f"{int(pct)}%", fill=EINK_FG, font=font)
    ctx.y = y + bh + margin_bottom


@register_block("signal_strength_meter")
def render_signal_strength_meter(ctx: RenderContext, block: dict) -> None:
    """阶梯信号格指示组件。"""
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 6) * ctx.scale)
    bars = int(block.get("bars", 4))
    max_bars = 4
    y = ctx.y
    x = ctx.x_offset + margin_x

    for i in range(max_bars):
        bx = x + i * 5
        bh = (i + 1) * 3 + 2
        by = y + 14 - bh
        fill = EINK_FG if i < bars else None
        _draw_box(ctx.draw, (bx, by, bx + 3, y + 14), outline=EINK_FG, fill=fill)

    ctx.y = y + 16 + margin_bottom


@register_block("speed_gauge")
def render_speed_gauge(ctx: RenderContext, block: dict) -> None:
    """半圆速度与刻度盘。"""
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 6) * ctx.scale)
    pct = float(block.get("pct", 65))
    r = 20
    cx = ctx.x_offset + margin_x + r
    cy = ctx.y + r

    # 半圆弧
    ctx.draw.arc((cx - r, cy - r, cx + r, cy + r), start=180, end=0, fill=EINK_FG, width=1)
    # 指针
    rad = math.radians(180 + (pct / 100.0) * 180)
    px = cx + int((r - 3) * math.cos(rad))
    py = cy + int((r - 3) * math.sin(rad))
    ctx.draw.line((cx, cy, px, py), fill=EINK_FG, width=2)
    ctx.y = cy + margin_bottom + 4


@register_block("funnel_chart")
def render_funnel_chart(ctx: RenderContext, block: dict) -> None:
    """漏斗阶梯转化图。"""
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 6) * ctx.scale)
    layers = block.get("layers") or [100, 75, 45, 20]
    w = ctx.available_width - margin_x * 2
    y = ctx.y
    cx = ctx.x_offset + margin_x + w // 2

    for l in layers:
        lw = int(w * (l / 100.0))
        _draw_box(ctx.draw, (cx - lw // 2, y, cx + lw // 2, y + 6), outline=EINK_FG, fill=None)
        y += 8
    ctx.y = y + margin_bottom


@register_block("pyramid_bars")
def render_pyramid_bars(ctx: RenderContext, block: dict) -> None:
    """中心对称金字塔对比条。"""
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 6) * ctx.scale)
    left_v = float(block.get("left", 45))
    right_v = float(block.get("right", 70))
    w = ctx.available_width - margin_x * 2
    cx = ctx.x_offset + margin_x + w // 2
    y = ctx.y
    half_w = w // 2 - 10

    # 左条
    lw = int(half_w * (left_v / 100.0))
    _draw_box(ctx.draw, (cx - lw, y, cx - 2, y + 8), fill=EINK_FG)
    # 右条
    rw = int(half_w * (right_v / 100.0))
    _draw_box(ctx.draw, (cx + 2, y, cx + rw, y + 8), outline=EINK_FG, width=1)
    ctx.y = y + 10 + margin_bottom


@register_block("spark_bar")
def render_spark_bar(ctx: RenderContext, block: dict) -> None:
    """迷你柱状走势图 (Mini Sparkline Bar)。"""
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 6) * ctx.scale)
    vals = block.get("values") or [4, 7, 2, 8, 5, 9, 6, 8, 10, 6]
    y = ctx.y
    x = ctx.x_offset + margin_x
    max_v = max(max(vals) if vals else 10, 1)

    for i, v in enumerate(vals):
        bh = int((v / max_v) * 16)
        _draw_box(ctx.draw, (x + i * 5, y + 16 - bh, x + i * 5 + 3, y + 16), fill=EINK_FG)
    ctx.y = y + 18 + margin_bottom
