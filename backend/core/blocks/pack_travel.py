"""
InkSight 扩充排版组件库 7：电商、出行与天气传感组件 (Weather, Travel & Commerce)
包含：
91. sunrise_sunset_arc: 日出日落太阳运行轨迹弧线
92. moon_phase_circle: 月相阴晴圆缺图形
93. flight_boarding_pass: 登机牌条码与航段卡
94. train_ticket_segment: 高铁火车发到站双箭头行
95. wind_rose_compass: 风向八卦罗盘指示
96. price_tag_discount: 打折标签与划线现价
97. parcel_tracking_step: 物流快递签收节点
98. currency_exchange_card: 实时汇率双币折算条
99. hotel_booking_strip: 酒店入住退房天数条
100. subway_line_pill: 地铁线路换乘彩色胶囊
101. parking_spot_counter: 车位空余计数看板
102. charging_pile_status: 电动车充电桩功率电流
103. fuel_price_board: 92/95汽油标号油价牌
104. highway_toll_gate: 高速收费站通行指示
105. barometric_pressure_trend: 气压趋势变动微线
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


def _draw_box(draw: ImageDraw.ImageDraw, bbox: tuple[int, int, int, int], outline=EINK_FG, fill=None, width=1):
    draw.rectangle(bbox, outline=outline, fill=fill, width=width)


@register_block("sunrise_sunset_arc")
def render_sunrise_sunset_arc(ctx: RenderContext, block: dict) -> None:
    """日出日落太阳轨迹弧。"""
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 6) * ctx.scale)
    rise = str(block.get("rise", "05:42"))
    set_t = str(block.get("set", "18:25"))
    x = ctx.x_offset + margin_x
    y = ctx.y
    w = ctx.available_width - margin_x * 2
    r = 30
    cx = x + w // 2
    cy = y + r

    # 地平线
    ctx.draw.line((cx - r - 10, cy, cx + r + 10, cy), fill=EINK_FG, width=1)
    # 半圆弧
    ctx.draw.arc((cx - r, cy - r, cx + r, cy + r), start=180, end=0, fill=EINK_FG, width=1)
    # 太阳小圆
    ctx.draw.ellipse((cx - 3, cy - r - 3, cx + 3, cy - r + 3), fill=EINK_FG)

    font = load_font("noto_serif_regular", int(8 * ctx.scale))
    ctx.draw.text((cx - r - 20, cy + 2), f"RISE {rise}", fill=EINK_FG, font=font)
    ctx.draw.text((cx + r - 10, cy + 2), f"SET {set_t}", fill=EINK_FG, font=font)
    ctx.y = cy + 14 + margin_bottom


@register_block("moon_phase_circle")
def render_moon_phase_circle(ctx: RenderContext, block: dict) -> None:
    """月相图形。"""
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 4) * ctx.scale)
    phase_name = str(block.get("name", "WAXING GIBBOUS · 盈凸月"))
    x = ctx.x_offset + margin_x
    y = ctx.y

    ctx.draw.ellipse((x, y, x + 16, y + 16), outline=EINK_FG, width=1)
    ctx.draw.chord((x, y, x + 16, y + 16), start=-90, end=90, fill=EINK_FG)
    font = load_font("noto_serif_regular", int(9 * ctx.scale))
    ctx.draw.text((x + 22, y + 2), phase_name, fill=EINK_FG, font=font)
    ctx.y = y + 18 + margin_bottom


@register_block("flight_boarding_pass")
def render_flight_boarding_pass(ctx: RenderContext, block: dict) -> None:
    """登机牌航班卡。"""
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 6) * ctx.scale)
    flight = str(block.get("flight", "CA1835"))
    origin = str(block.get("from", "PEK"))
    dest = str(block.get("to", "SHA"))
    gate = str(block.get("gate", "GATE C28"))
    x = ctx.x_offset + margin_x
    y = ctx.y
    w = ctx.available_width - margin_x * 2

    _draw_box(ctx.draw, (x, y, x + w, y + 28), outline=EINK_FG, width=1)
    font_b = load_font("noto_serif_bold", int(12 * ctx.scale))
    font_r = load_font("noto_serif_regular", int(8 * ctx.scale))
    ctx.draw.text((x + 8, y + 3), f"{origin} -> {dest}", fill=EINK_FG, font=font_b)
    ctx.draw.text((x + 8, y + 16), f"{flight} · {gate}", fill=EINK_FG, font=font_r)
    ctx.y = y + 30 + margin_bottom


@register_block("train_ticket_segment")
def render_train_ticket_segment(ctx: RenderContext, block: dict) -> None:
    """高铁火车车次条。"""
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 4) * ctx.scale)
    train_no = str(block.get("no", "G102"))
    dep = str(block.get("dep", "上海虹桥 08:00"))
    arr = str(block.get("arr", "北京南 12:28"))
    x = ctx.x_offset + margin_x
    y = ctx.y

    font_b = load_font("noto_serif_bold", int(9 * ctx.scale))
    font_r = load_font("noto_serif_regular", int(8 * ctx.scale))
    ctx.draw.text((x, y), f"[{train_no}]", fill=EINK_FG, font=font_b)
    ctx.draw.text((x + 50, y), f"{dep} ==> {arr}", fill=EINK_FG, font=font_r)
    ctx.y = y + 13 + margin_bottom


@register_block("wind_rose_compass")
def render_wind_rose_compass(ctx: RenderContext, block: dict) -> None:
    """风向罗盘。"""
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 4) * ctx.scale)
    dir_str = str(block.get("dir", "NNE 3.2m/s"))
    x = ctx.x_offset + margin_x
    y = ctx.y

    ctx.draw.line((x + 6, y, x + 6, y + 12), fill=EINK_FG, width=1)
    ctx.draw.line((x, y + 6, x + 12, y + 6), fill=EINK_FG, width=1)
    ctx.draw.line((x + 6, y, x + 10, y + 2), fill=EINK_FG, width=1)
    font = load_font("noto_serif_regular", int(8 * ctx.scale))
    ctx.draw.text((x + 18, y + 1), f"WIND: {dir_str}", fill=EINK_FG, font=font)
    ctx.y = y + 14 + margin_bottom


@register_block("price_tag_discount")
def render_price_tag_discount(ctx: RenderContext, block: dict) -> None:
    """打折与划线价标签。"""
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 4) * ctx.scale)
    price = str(block.get("price", "¥199.00"))
    orig = str(block.get("orig", "¥299.00"))
    x = ctx.x_offset + margin_x
    y = ctx.y

    font_p = load_font("noto_serif_bold", int(11 * ctx.scale))
    font_o = load_font("noto_serif_regular", int(8 * ctx.scale))
    ctx.draw.text((x, y), price, fill=EINK_FG, font=font_p)
    tb = safe_font_bbox(font_p, price)
    ox = x + (tb[2] - tb[0]) + 10
    ctx.draw.text((ox, y + 3), orig, fill=EINK_FG, font=font_o)
    tb_o = safe_font_bbox(font_o, orig)
    ctx.draw.line((ox, y + 7, ox + (tb_o[2] - tb_o[0]), y + 7), fill=EINK_FG, width=1)
    ctx.y = y + 15 + margin_bottom


@register_block("parcel_tracking_step")
def render_parcel_tracking_step(ctx: RenderContext, block: dict) -> None:
    """快递派送状态节点。"""
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 4) * ctx.scale)
    pkg = str(block.get("pkg", "SF-Express: 已到达智能快递柜"))
    x = ctx.x_offset + margin_x
    y = ctx.y

    font = load_font("noto_serif_regular", int(8 * ctx.scale))
    _draw_box(ctx.draw, (x, y + 1, x + 6, y + 7), fill=EINK_FG)
    ctx.draw.text((x + 12, y), pkg, fill=EINK_FG, font=font)
    ctx.y = y + 12 + margin_bottom


@register_block("currency_exchange_card")
def render_currency_exchange_card(ctx: RenderContext, block: dict) -> None:
    """双币汇率换算行。"""
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 4) * ctx.scale)
    fx = str(block.get("fx", "100 USD = 714.20 CNY"))
    x = ctx.x_offset + margin_x
    y = ctx.y

    font = load_font("noto_serif_bold", int(9 * ctx.scale))
    ctx.draw.text((x, y), fx, fill=EINK_FG, font=font)
    ctx.y = y + 13 + margin_bottom


@register_block("hotel_booking_strip")
def render_hotel_booking_strip(ctx: RenderContext, block: dict) -> None:
    """酒店入住退房条。"""
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 4) * ctx.scale)
    hotel = str(block.get("hotel", "Park Hyatt · 1 Night"))
    x = ctx.x_offset + margin_x
    y = ctx.y

    font = load_font("noto_serif_regular", int(8 * ctx.scale))
    ctx.draw.text((x, y), f"HOTEL: {hotel}", fill=EINK_FG, font=font)
    ctx.y = y + 12 + margin_bottom


@register_block("subway_line_pill")
def render_subway_line_pill(ctx: RenderContext, block: dict) -> None:
    """地铁线路换乘胶囊。"""
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 4) * ctx.scale)
    line = str(block.get("line", "LINE 2"))
    station = str(block.get("station", "人民广场 (Next: 2m)"))
    x = ctx.x_offset + margin_x
    y = ctx.y

    font = load_font("noto_serif_bold", int(8 * ctx.scale))
    tb = safe_font_bbox(font, line)
    bw = (tb[2] - tb[0]) + 8
    _draw_box(ctx.draw, (x, y, x + bw, y + 12), fill=EINK_FG)
    ctx.draw.text((x + 4, y + 1), line, fill=EINK_BG, font=font)
    font_s = load_font("noto_serif_regular", int(8 * ctx.scale))
    ctx.draw.text((x + bw + 8, y + 1), station, fill=EINK_FG, font=font_s)
    ctx.y = y + 14 + margin_bottom


@register_block("parking_spot_counter")
def render_parking_spot_counter(ctx: RenderContext, block: dict) -> None:
    """车位剩余指示牌。"""
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 4) * ctx.scale)
    spots = str(block.get("spots", "PARKING: 142 SPOTS"))
    x = ctx.x_offset + margin_x
    y = ctx.y

    font = load_font("noto_serif_regular", int(9 * ctx.scale))
    ctx.draw.text((x, y), spots, fill=EINK_FG, font=font)
    ctx.y = y + 13 + margin_bottom


@register_block("charging_pile_status")
def render_charging_pile_status(ctx: RenderContext, block: dict) -> None:
    """充电桩功率电流指示。"""
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 4) * ctx.scale)
    kw = str(block.get("kw", "EV CHARGE: 60kW (85%)"))
    x = ctx.x_offset + margin_x
    y = ctx.y

    font = load_font("noto_serif_regular", int(8 * ctx.scale))
    ctx.draw.text((x, y), kw, fill=EINK_FG, font=font)
    ctx.y = y + 12 + margin_bottom


@register_block("fuel_price_board")
def render_fuel_price_board(ctx: RenderContext, block: dict) -> None:
    """汽油标号油价行。"""
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 4) * ctx.scale)
    p92 = str(block.get("p92", "92#: 7.85"))
    p95 = str(block.get("p95", "95#: 8.36"))
    x = ctx.x_offset + margin_x
    y = ctx.y

    font = load_font("noto_serif_regular", int(8 * ctx.scale))
    ctx.draw.text((x, y), f"GAS: {p92} | {p95}", fill=EINK_FG, font=font)
    ctx.y = y + 12 + margin_bottom


@register_block("highway_toll_gate")
def render_highway_toll_gate(ctx: RenderContext, block: dict) -> None:
    """高速通行指示。"""
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 4) * ctx.scale)
    gate = str(block.get("gate", "ETC LANE 02 · OPEN"))
    x = ctx.x_offset + margin_x
    y = ctx.y

    font = load_font("noto_serif_regular", int(8 * ctx.scale))
    ctx.draw.text((x, y), f"TOLL: {gate}", fill=EINK_FG, font=font)
    ctx.y = y + 12 + margin_bottom


@register_block("barometric_pressure_trend")
def render_barometric_pressure_trend(ctx: RenderContext, block: dict) -> None:
    """气压走势指示。"""
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 4) * ctx.scale)
    hpa = str(block.get("hpa", "1013.2 hPa (STEADY)"))
    x = ctx.x_offset + margin_x
    y = ctx.y

    font = load_font("noto_serif_regular", int(8 * ctx.scale))
    ctx.draw.text((x, y), f"BARO: {hpa}", fill=EINK_FG, font=font)
    ctx.y = y + 12 + margin_bottom
