"""
InkSight 扩充排版组件库 5：生活健康与传感器组件 (Life & Health Widgets)
包含：
61. water_intake_cups: 喝水杯数象形阵列
62. step_counter_meter: 计步进度条与目标步数
63. standing_hours_bar: 站立小时打卡条
64. calorie_burn_card: 卡路里热量消耗卡片
65. heart_rate_bpm: 心率脉搏心电图微行
66. air_quality_chip: AQI 空气质量指标微芯片
67. uv_index_badge: 紫外线强度防晒徽章
68. room_comfort_meter: 室内温湿度舒适度仪表
69. medicine_reminder_box: 用药与提醒复选框
70. coffee_caffeine_scale: 咖啡因摄入量刻度
71. eye_care_break_hint: 20-20-20 护眼休息提醒
72. body_weight_trend_dot: 体重趋势走势微标
73. noise_level_decibel: 环境噪音分贝检测
74. sedentary_alert_pill: 久坐运动提醒胶囊
75. plant_watering_status: 绿植浇水状态条
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
)
from .context import RenderContext
from .registry import register_block

logger = logging.getLogger(__name__)


def _draw_box(draw: ImageDraw.ImageDraw, bbox: tuple[int, int, int, int], outline=EINK_FG, fill=None, width=1):
    draw.rectangle(bbox, outline=outline, fill=fill, width=width)


@register_block("water_intake_cups")
def render_water_intake_cups(ctx: RenderContext, block: dict) -> None:
    """喝水杯数象形阵列 (8杯水)。"""
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 6) * ctx.scale)
    drank = int(block.get("drank", 5))
    total = 8
    x = ctx.x_offset + margin_x
    y = ctx.y

    font = load_font("noto_serif_regular", int(8 * ctx.scale))
    ctx.draw.text((x, y), "WATER:", fill=EINK_FG, font=font)
    sx = x + 44
    for i in range(total):
        bx = sx + i * 11
        fill = EINK_FG if i < drank else None
        _draw_box(ctx.draw, (bx, y, bx + 7, y + 10), outline=EINK_FG, fill=fill)
    ctx.y = y + 12 + margin_bottom


@register_block("step_counter_meter")
def render_step_counter_meter(ctx: RenderContext, block: dict) -> None:
    """步数统计量规。"""
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 6) * ctx.scale)
    steps = int(block.get("steps", 8420))
    target = int(block.get("target", 10000))
    x = ctx.x_offset + margin_x
    y = ctx.y
    w = ctx.available_width - margin_x * 2

    font_b = load_font("noto_serif_bold", int(10 * ctx.scale))
    font_r = load_font("noto_serif_regular", int(8 * ctx.scale))
    ctx.draw.text((x, y), f"{steps} STEPS", fill=EINK_FG, font=font_b)
    ctx.draw.text((x + 90, y + 2), f"/ {target}", fill=EINK_FG, font=font_r)
    by = y + 13
    _draw_box(ctx.draw, (x, by, x + w, by + 5), outline=EINK_FG, width=1)
    fw = int(w * (min(1.0, steps / target)))
    if fw > 0:
        _draw_box(ctx.draw, (x, by, x + fw, by + 5), fill=EINK_FG)
    ctx.y = by + 7 + margin_bottom


@register_block("standing_hours_bar")
def render_standing_hours_bar(ctx: RenderContext, block: dict) -> None:
    """站立小时达成条 (12小时)。"""
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 4) * ctx.scale)
    hours = int(block.get("hours", 9))
    x = ctx.x_offset + margin_x
    y = ctx.y

    font = load_font("noto_serif_regular", int(9 * ctx.scale))
    ctx.draw.text((x, y), f"STAND: {hours}/12 HRS", fill=EINK_FG, font=font)
    ctx.y = y + 13 + margin_bottom


@register_block("calorie_burn_card")
def render_calorie_burn_card(ctx: RenderContext, block: dict) -> None:
    """卡路里消耗指标卡。"""
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 4) * ctx.scale)
    kcal = str(block.get("kcal", "540 kcal"))
    x = ctx.x_offset + margin_x
    y = ctx.y

    font = load_font("noto_serif_bold", int(10 * ctx.scale))
    ctx.draw.text((x, y), f"ACTIVE ENERGY: {kcal}", fill=EINK_FG, font=font)
    ctx.y = y + 14 + margin_bottom


@register_block("heart_rate_bpm")
def render_heart_rate_bpm(ctx: RenderContext, block: dict) -> None:
    """心率脉搏微行。"""
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 4) * ctx.scale)
    bpm = str(block.get("bpm", "68 BPM"))
    x = ctx.x_offset + margin_x
    y = ctx.y

    font_b = load_font("noto_serif_bold", int(10 * ctx.scale))
    ctx.draw.text((x, y), f"PULSE: {bpm}", fill=EINK_FG, font=font_b)
    ctx.y = y + 14 + margin_bottom


@register_block("air_quality_chip")
def render_air_quality_chip(ctx: RenderContext, block: dict) -> None:
    """空气质量 AQI 徽章。"""
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 4) * ctx.scale)
    aqi = str(block.get("aqi", "32 EXCELLENT"))
    x = ctx.x_offset + margin_x
    y = ctx.y

    font = load_font("noto_serif_regular", int(9 * ctx.scale))
    text = f"AQI: {aqi}"
    tb = safe_font_bbox(font, text)
    bw = (tb[2] - tb[0]) + 8
    _draw_box(ctx.draw, (x, y, x + bw, y + 13), outline=EINK_FG, width=1)
    ctx.draw.text((x + 4, y + 1), text, fill=EINK_FG, font=font)
    ctx.y = y + 15 + margin_bottom


@register_block("uv_index_badge")
def render_uv_index_badge(ctx: RenderContext, block: dict) -> None:
    """紫外线指数徽章。"""
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 4) * ctx.scale)
    uv = str(block.get("uv", "UV 2 (LOW)"))
    x = ctx.x_offset + margin_x
    y = ctx.y

    font = load_font("noto_serif_regular", int(8 * ctx.scale))
    tb = safe_font_bbox(font, uv)
    bw = (tb[2] - tb[0]) + 8
    _draw_box(ctx.draw, (x, y, x + bw, y + 12), fill=EINK_FG)
    ctx.draw.text((x + 4, y + 1), uv, fill=EINK_BG, font=font)
    ctx.y = y + 14 + margin_bottom


@register_block("room_comfort_meter")
def render_room_comfort_meter(ctx: RenderContext, block: dict) -> None:
    """室内温湿度舒适度仪表。"""
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 4) * ctx.scale)
    temp = str(block.get("temp", "24.5°C"))
    hum = str(block.get("hum", "52%"))
    x = ctx.x_offset + margin_x
    y = ctx.y

    font = load_font("noto_serif_regular", int(9 * ctx.scale))
    ctx.draw.text((x, y), f"INDOOR: {temp} / {hum} (COMFORT)", fill=EINK_FG, font=font)
    ctx.y = y + 13 + margin_bottom


@register_block("medicine_reminder_box")
def render_medicine_reminder_box(ctx: RenderContext, block: dict) -> None:
    """用药与维生素复选框。"""
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 4) * ctx.scale)
    med = str(block.get("med", "Vitamin C 1000mg"))
    done = bool(block.get("done", True))
    x = ctx.x_offset + margin_x
    y = ctx.y

    _draw_box(ctx.draw, (x, y + 1, x + 8, y + 9), outline=EINK_FG, fill=EINK_FG if done else None)
    font = load_font("noto_serif_regular", int(9 * ctx.scale))
    ctx.draw.text((x + 14, y), f"MED: {med}", fill=EINK_FG, font=font)
    ctx.y = y + 13 + margin_bottom


@register_block("coffee_caffeine_scale")
def render_coffee_caffeine_scale(ctx: RenderContext, block: dict) -> None:
    """咖啡因摄入量指示。"""
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 4) * ctx.scale)
    mg = str(block.get("mg", "140mg (2 CUPS)"))
    x = ctx.x_offset + margin_x
    y = ctx.y

    font = load_font("noto_serif_regular", int(9 * ctx.scale))
    ctx.draw.text((x, y), f"CAFFEINE: {mg}", fill=EINK_FG, font=font)
    ctx.y = y + 13 + margin_bottom


@register_block("eye_care_break_hint")
def render_eye_care_break_hint(ctx: RenderContext, block: dict) -> None:
    """护眼休息提醒条。"""
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 4) * ctx.scale)
    hint = str(block.get("hint", "20-20-20 Rule: Look 20ft away"))
    x = ctx.x_offset + margin_x
    y = ctx.y

    font = load_font("noto_serif_regular", int(8 * ctx.scale))
    ctx.draw.text((x, y), f"EYE CARE: {hint}", fill=EINK_FG, font=font)
    ctx.y = y + 12 + margin_bottom


@register_block("body_weight_trend_dot")
def render_body_weight_trend_dot(ctx: RenderContext, block: dict) -> None:
    """体重趋势走势微标。"""
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 4) * ctx.scale)
    wt = str(block.get("weight", "68.2 kg (-0.4)"))
    x = ctx.x_offset + margin_x
    y = ctx.y

    font = load_font("noto_serif_regular", int(9 * ctx.scale))
    ctx.draw.text((x, y), f"WEIGHT: {wt}", fill=EINK_FG, font=font)
    ctx.y = y + 13 + margin_bottom


@register_block("noise_level_decibel")
def render_noise_level_decibel(ctx: RenderContext, block: dict) -> None:
    """环境噪音分贝微行。"""
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 4) * ctx.scale)
    db = str(block.get("db", "42 dB (QUIET)"))
    x = ctx.x_offset + margin_x
    y = ctx.y

    font = load_font("noto_serif_regular", int(8 * ctx.scale))
    ctx.draw.text((x, y), f"NOISE: {db}", fill=EINK_FG, font=font)
    ctx.y = y + 12 + margin_bottom


@register_block("sedentary_alert_pill")
def render_sedentary_alert_pill(ctx: RenderContext, block: dict) -> None:
    """久坐运动提醒胶囊。"""
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 4) * ctx.scale)
    mins = str(block.get("mins", "Sit 55m -> Stand up"))
    x = ctx.x_offset + margin_x
    y = ctx.y

    font = load_font("noto_serif_regular", int(8 * ctx.scale))
    tb = safe_font_bbox(font, mins)
    bw = (tb[2] - tb[0]) + 8
    _draw_box(ctx.draw, (x, y, x + bw, y + 12), outline=EINK_FG, width=1)
    ctx.draw.text((x + 4, y + 1), mins, fill=EINK_FG, font=font)
    ctx.y = y + 14 + margin_bottom


@register_block("plant_watering_status")
def render_plant_watering_status(ctx: RenderContext, block: dict) -> None:
    """绿植浇水状态条。"""
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 4) * ctx.scale)
    status = str(block.get("status", "Monstera: Moist (Next: 3d)"))
    x = ctx.x_offset + margin_x
    y = ctx.y

    font = load_font("noto_serif_regular", int(8 * ctx.scale))
    ctx.draw.text((x, y), f"PLANT: {status}", fill=EINK_FG, font=font)
    ctx.y = y + 12 + margin_bottom
