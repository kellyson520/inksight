"""
时序走势与气象图表组件模块 (Charts & Visual Time-series Blocks)
包含：sparkline, temp_chart, forecast_cards
"""
from __future__ import annotations

import logging
from typing import Any

from PIL import Image

from core.patterns.utils import EINK_BG, EINK_FG, has_cjk, load_font
from .context import RenderContext
from .registry import register_block

logger = logging.getLogger(__name__)


def _num(v: Any) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def render_sparkline(ctx: RenderContext, block: dict) -> None:
    field_name = block.get("field", "sparkline_data")
    raw_data = ctx.get_field(field_name)
    if not isinstance(raw_data, list) or not raw_data:
        return

    val_key = block.get("value_key", "value")
    values: list[float] = []
    for item in raw_data:
        if isinstance(item, (int, float)):
            values.append(float(item))
        elif isinstance(item, dict) and val_key in item:
            try:
                values.append(float(item[val_key]))
            except (ValueError, TypeError):
                continue

    if len(values) < 2:
        return

    scale = ctx.scale
    chart_height = int(block.get("height", 46) * scale)
    line_width = int(block.get("line_width", 2) * scale) or 1
    margin_x = int(block.get("margin_x", 16) * scale)
    margin_bottom = int(block.get("margin_bottom", 8) * scale)
    show_baseline = bool(block.get("show_baseline", True))
    show_endpoints = bool(block.get("show_endpoints", True))
    area_shading = bool(block.get("area_shading", True))
    show_extrema = bool(block.get("show_extrema", False))
    show_time_axis = bool(block.get("show_time_axis", False))

    color_name = block.get("color", "red" if ctx.colors >= 3 else "black")
    line_fill = ctx.color_index(color_name, default=EINK_FG)

    width = ctx.available_width - margin_x * 2
    if width <= 0:
        return

    x0 = ctx.x_offset + margin_x
    y_top = ctx.y + int(4 * scale)
    y_bottom = y_top + chart_height - int(6 * scale)
    usable_h = y_bottom - y_top

    min_v = min(values)
    max_v = max(values)
    span = max_v - min_v
    if span <= 0:
        span = 1.0

    n = len(values)
    step = width / (n - 1)

    points: list[tuple[float, float]] = []
    for i, v in enumerate(values):
        px = x0 + i * step
        ratio = (v - min_v) / span
        py = y_bottom - (ratio * usable_h)
        points.append((px, py))

    base_val = float(block.get("baseline_value", values[0]))
    base_ratio = (base_val - min_v) / span
    base_y = y_bottom - (base_ratio * usable_h) if (0.0 <= base_ratio <= 1.0) else y_bottom

    # 1. 墨水屏网点立体阴影填充 (Area Shading)
    if area_shading and len(points) >= 2:
        shade_color = line_fill
        for i in range(len(points) - 1):
            px0, py0 = points[i]
            px1, py1 = points[i + 1]
            x_start = int(px0)
            x_end = int(px1)
            for x in range(x_start, x_end):
                progress = (x - px0) / max(1.0, px1 - px0)
                curve_y = int(py0 + progress * (py1 - py0))
                shade_bottom = int(min(y_bottom, max(curve_y, base_y)))
                for y in range(curve_y + 2, shade_bottom):
                    if (x + y) % 4 == 0 and x % 2 == 0:
                        ctx.draw.point((x, y), fill=shade_color)

    # 2. 参考基准虚线
    if show_baseline and 0.0 <= base_ratio <= 1.0:
        dash_w = int(4 * scale) or 3
        dash_gap = int(3 * scale) or 2
        cur_x = x0
        while cur_x < x0 + width:
            seg_end = min(cur_x + dash_w, x0 + width)
            ctx.draw.line([(cur_x, base_y), (seg_end, base_y)], fill=EINK_FG, width=1)
            cur_x += dash_w + dash_gap

    # 3. 连续主折线
    for i in range(1, len(points)):
        ctx.draw.line([points[i - 1], points[i]], fill=line_fill, width=line_width)

    # 4. 首尾关键点指示
    if show_endpoints and len(points) >= 2:
        r = int(2.5 * scale) or 2
        sx, sy = points[0]
        ctx.draw.ellipse([sx - r, sy - r, sx + r, sy + r], fill=EINK_BG)
        ctx.draw.ellipse([sx - r, sy - r, sx + r, sy + r], outline=line_fill, width=1)
        ex, ey = points[-1]
        ctx.draw.ellipse([ex - r, ey - r, ex + r, ey + r], fill=line_fill)

    # 5. 极值标注
    if show_extrema:
        max_idx = values.index(max_v)
        min_idx = values.index(min_v)
        font_ext = load_font("noto_serif_regular", int(10 * scale))
        hx, hy = points[max_idx]
        htxt = f"{max_v:,.1f}"
        hbbox = font_ext.getbbox(htxt)
        htw = hbbox[2] - hbbox[0]
        ctx.draw.text((hx - htw // 2, hy - 12), htxt, fill=EINK_FG, font=font_ext)

        lx, ly = points[min_idx]
        ltxt = f"{min_v:,.1f}"
        lbbox = font_ext.getbbox(ltxt)
        ltw = lbbox[2] - lbbox[0]
        ctx.draw.text((lx - ltw // 2, ly + 4), ltxt, fill=EINK_FG, font=font_ext)

    # 6. 时间轴刻度
    if show_time_axis:
        font_axis = load_font("noto_serif_light", int(9 * scale))
        start_label = block.get("start_label", "24h前")
        end_label = block.get("end_label", "最新")
        ctx.draw.text((x0, y_bottom + 2), start_label, fill=EINK_FG, font=font_axis)
        ebbox = font_axis.getbbox(end_label)
        ctx.draw.text((x0 + width - (ebbox[2] - ebbox[0]), y_bottom + 2), end_label, fill=EINK_FG, font=font_axis)
        ctx.y = y_top + chart_height + margin_bottom + int(10 * scale)
    else:
        ctx.y = y_top + chart_height + margin_bottom


def render_temp_chart(ctx: RenderContext, block: dict) -> None:
    field_name = block.get("field", "forecast")
    items = ctx.get_field(field_name)
    if not isinstance(items, list) or not items:
        return

    max_points = int(block.get("max_points", 4))
    high_field = block.get("high_field", block.get("temp_field", "temp_max"))
    low_field = block.get("low_field", "temp_min")
    label_field = block.get("label_field", "day")

    highs: list[float] = []
    lows: list[float] = []
    labels = []

    for item in items[:max_points]:
        if not isinstance(item, dict):
            continue
        h_raw = item.get(high_field)
        l_raw = item.get(low_field)
        if h_raw is None or l_raw is None:
            continue
        highs.append(_num(h_raw))
        lows.append(_num(l_raw))
        labels.append(str(item.get(label_field, "")))

    if not highs:
        return

    all_temps = highs + lows
    min_t = min(all_temps)
    max_t = max(all_temps)
    if max_t == min_t:
        max_t = min_t + 1

    margin_x = block.get("margin_x")
    if margin_x is not None:
        margin_x = int(margin_x * ctx.scale)
    else:
        margin_x = int(ctx.screen_w * 0.08)

    chart_height = int(block.get("height", 40) * ctx.scale)
    extra_right_margin = int(block.get("right_margin", 8) * ctx.scale)
    width = ctx.available_width - margin_x * 2 - extra_right_margin
    if width <= 0:
        return

    x0 = ctx.x_offset + margin_x
    bottom_pad = int(block.get("bottom_pad", 0) * ctx.scale)
    y_bottom = ctx.y + chart_height - bottom_pad
    y_top = y_bottom - chart_height

    n = len(highs)
    step = 0 if n == 1 else width / (n - 1)

    high_coords: list[tuple[float, float]] = []
    low_coords: list[tuple[float, float]] = []
    for idx, (h_temp, l_temp) in enumerate(zip(highs, lows)):
        x = x0 + step * idx
        ratio_h = (h_temp - min_t) / (max_t - min_t)
        ratio_l = (l_temp - min_t) / (max_t - min_t)
        y_h = y_bottom - ratio_h * (chart_height - 8)
        y_l = y_bottom - ratio_l * (chart_height - 8)
        high_coords.append((x, y_h))
        low_coords.append((x, y_l))

    for i in range(1, len(high_coords)):
        ctx.draw.line([high_coords[i - 1], high_coords[i]], fill=EINK_FG, width=1)
    for i in range(1, len(low_coords)):
        ctx.draw.line([low_coords[i - 1], low_coords[i]], fill=EINK_FG, width=1)

    font = load_font("noto_serif_light", int(10 * ctx.scale))
    for (xh, yh), (xl, yl), h_temp, l_temp, label in zip(high_coords, low_coords, highs, lows, labels):
        r = int(2 * ctx.scale) or 1
        ctx.draw.ellipse([xh - r, yh - r, xh + r, yh + r], fill=EINK_FG)
        ctx.draw.ellipse([xl - r, yl - r, xl + r, yl + r], fill=EINK_BG)
        ctx.draw.ellipse([xl - r, yl - r, xl + r, yl + r], outline=EINK_FG, width=1)

        temp_text_high = str(int(round(h_temp)))
        hbbox = font.getbbox(temp_text_high)
        htw = hbbox[2] - hbbox[0]
        hth = hbbox[3] - hbbox[1]
        ctx.draw.text((xh - htw / 2, y_top - hth - 2), temp_text_high, fill=EINK_FG, font=font)

        if label:
            lbbox = font.getbbox(label)
            lw = lbbox[2] - lbbox[0]
            ctx.draw.text((xl - lw / 2, y_bottom + 4), label, fill=EINK_FG, font=font)

    ctx.y = y_bottom + int(18 * ctx.scale)


def render_forecast_cards(ctx: RenderContext, block: dict) -> None:
    """Render multi-day forecast cards similar to the reference UI."""
    from core.patterns.utils import get_weather_icon

    field_name = block.get("field", "forecast")
    items = ctx.get_field(field_name)
    if not isinstance(items, list) or not items:
        return

    max_items = int(block.get("max_items", 4))
    items = [it for it in items if isinstance(it, dict)][:max_items]
    if not items:
        return

    scale = ctx.scale
    day_field = block.get("day_field", "day")
    date_field = block.get("date_field", "date")
    desc_field = block.get("desc_field", "desc")
    code_field = block.get("code_field", "code")
    temp_min_field = block.get("temp_min_field", "temp_min")
    temp_max_field = block.get("temp_max_field", "temp_max")
    temp_range_field = block.get("temp_range_field", "temp_range")
    show_desc = bool(block.get("show_desc", True))
    show_temp = bool(block.get("show_temp", True))
    margin_x = block.get("margin_x")
    if margin_x is not None:
        margin_x = int(margin_x * scale)
    else:
        margin_x = int(ctx.screen_w * 0.02)
    gap = int(block.get("gap", 6) * scale)
    day_gap = int(block.get("day_gap", 3) * scale)
    date_gap = int(block.get("date_gap", 5) * scale)
    icon_gap = int(block.get("icon_gap", 4) * scale)
    desc_gap = int(block.get("desc_gap", 3) * scale)
    margin_bottom = int(block.get("margin_bottom", 4) * scale)

    total_width = ctx.available_width - margin_x * 2
    n = len(items)
    card_min_width = int(block.get("card_min_width", 40) * scale)
    requested_card_width = block.get("card_width")
    if requested_card_width is not None:
        card_width = max(card_min_width, int(requested_card_width * scale))
    else:
        card_width = max(card_min_width, (total_width - gap * (n - 1)) // n)

    sample_text = " ".join(
        f"{item.get(day_field, '')} {item.get(date_field, '')} {item.get(desc_field, '')}"
        for item in items
    )
    default_day_font = "noto_serif_regular" if has_cjk(sample_text) else "lora_regular"
    default_date_font = "noto_serif_light" if has_cjk(sample_text) else "inter_medium"
    default_desc_font = "noto_serif_light" if has_cjk(sample_text) else "lora_regular"
    default_temp_font = "noto_serif_light" if has_cjk(sample_text) else "inter_medium"
    font_day = load_font(block.get("day_font", default_day_font), int(block.get("day_font_size", 14) * scale))
    font_date = load_font(block.get("date_font", default_date_font), int(block.get("date_font_size", 12) * scale))
    font_desc = load_font(block.get("desc_font", default_desc_font), int(block.get("desc_font_size", 12) * scale))
    font_temp = load_font(block.get("temp_font", default_temp_font), int(block.get("temp_font_size", 12) * scale))

    top_y = ctx.y
    card_bottom_max = top_y

    for idx, item in enumerate(items):
        x0 = ctx.x_offset + margin_x + idx * (card_width + gap)
        x_center = x0 + card_width // 2
        y = top_y

        day = str(item.get(day_field, ""))
        date = str(item.get(date_field, ""))
        desc = str(item.get(desc_field, ""))
        temp_min_raw = item.get(temp_min_field)
        temp_max_raw = item.get(temp_max_field)
        temp_label = ""
        if temp_min_raw is not None and temp_max_raw is not None:
            try:
                tmin = int(round(_num(temp_min_raw)))
                tmax = int(round(_num(temp_max_raw)))
                temp_label = f"{tmin}/{tmax}°"
            except (TypeError, ValueError):
                temp_label = ""
        if not temp_label:
            temp_label = str(item.get(temp_range_field, ""))
        code = item.get(code_field, -1)

        if day:
            bbox = font_day.getbbox(day)
            dw = bbox[2] - bbox[0]
            ctx.draw.text((x_center - dw / 2, y), day, fill=EINK_FG, font=font_day)
            y += (bbox[3] - bbox[1]) + day_gap

        if date:
            bbox = font_date.getbbox(date)
            tw = bbox[2] - bbox[0]
            th = bbox[3] - bbox[1]
            ctx.draw.text((x_center - tw / 2, y), date, fill=EINK_FG, font=font_date)
            y += th + date_gap

        icon_size = int(block.get("icon_size", 32) * scale)
        try:
            if isinstance(code, str):
                code_int = int(code)
            else:
                code_int = int(code)
        except (TypeError, ValueError):
            code_int = -1
        wx_icon = get_weather_icon(code_int) if code_int >= 0 else None
        if wx_icon:
            if wx_icon.size[0] != icon_size:
                wx_icon = wx_icon.resize((icon_size, icon_size), Image.LANCZOS)
            ctx.paste_icon(wx_icon, (int(x_center - icon_size / 2), int(y)))
            y += icon_size + icon_gap

        if show_desc and desc:
            bbox = font_desc.getbbox(desc)
            tw = bbox[2] - bbox[0]
            th = bbox[3] - bbox[1]
            ctx.draw.text((x_center - tw / 2, y), desc, fill=EINK_FG, font=font_desc)
            y += th + desc_gap

        if show_temp and temp_label:
            bbox = font_temp.getbbox(temp_label)
            tw = bbox[2] - bbox[0]
            th = bbox[3] - bbox[1]
            ctx.draw.text((x_center - tw / 2, y), temp_label, fill=EINK_FG, font=font_temp)
            y += th

        card_bottom_max = max(card_bottom_max, y)

    ctx.y = card_bottom_max + margin_bottom


# 注册所有图表类组件
register_block("sparkline", render_sparkline)
register_block("temp_chart", render_temp_chart)
register_block("forecast_cards", render_forecast_cards)
