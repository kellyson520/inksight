"""
InkSight 扩充排版组件库 4：智能日程、时间与打卡组件 (Calendar & Productivity)
包含：
46. analog_clock_face: 指针时钟表盘
47. pomodoro_timer_circle: 番茄钟剩余时间环
48. habit_check_matrix: 7天打卡习惯小方阵
49. countdown_flip_digit: 翻页式倒计时单字格
50. lunar_solar_strip: 农历/节气/公历横幅
51. week_agenda_row: 单日日程排期行
52. meeting_room_slot: 会议室与时段预订条
53. task_checkbox_item: 复选框清单条目
54. focus_duration_bar: 深度专注累计时长条
55. solar_term_badge: 二十四节气印章徽章
56. event_countdown_pill: 倒数纪念日小胶囊
57. day_progress_dots: 一日24小时时间刻度点阵
58. sleep_score_dial: 睡眠与作息质量圆环
59. weekly_goal_tracker: 周目标达成进度条
60. time_zone_duo: 双时区对照排版行
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


@register_block("analog_clock_face")
def render_analog_clock_face(ctx: RenderContext, block: dict) -> None:
    """指针时钟表盘。"""
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 6) * ctx.scale)
    r = 22
    x = ctx.x_offset + margin_x + r
    y = ctx.y + r

    # 外圈
    ctx.draw.ellipse((x - r, y - r, x + r, y + r), outline=EINK_FG, width=1)
    # 刻度
    for deg in (0, 90, 180, 270):
        rad = math.radians(deg)
        x1 = x + int((r - 4) * math.cos(rad))
        y1 = y + int((r - 4) * math.sin(rad))
        x2 = x + int(r * math.cos(rad))
        y2 = y + int(r * math.sin(rad))
        ctx.draw.line((x1, y1, x2, y2), fill=EINK_FG, width=1)
    # 指针 (默认 10:10)
    ctx.draw.line((x, y, x - 8, y - 8), fill=EINK_FG, width=2)
    ctx.draw.line((x, y, x + 12, y - 10), fill=EINK_FG, width=1)
    ctx.draw.ellipse((x - 2, y - 2, x + 2, y + 2), fill=EINK_FG)
    ctx.y = y + r + margin_bottom


@register_block("pomodoro_timer_circle")
def render_pomodoro_timer_circle(ctx: RenderContext, block: dict) -> None:
    """番茄钟剩余时间环。"""
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 6) * ctx.scale)
    mins = str(block.get("mins", "18:45"))
    x = ctx.x_offset + margin_x + 22
    y = ctx.y + 22

    ctx.draw.ellipse((x - 20, y - 20, x + 20, y + 20), outline=EINK_FG, width=1)
    ctx.draw.arc((x - 18, y - 18, x + 18, y + 18), start=-90, end=150, fill=EINK_FG, width=2)
    font = load_font("noto_serif_bold", int(9 * ctx.scale))
    tb = safe_font_bbox(font, mins)
    ctx.draw.text((x - (tb[2]-tb[0])//2, y - (tb[3]-tb[1])//2 - tb[1]), mins, fill=EINK_FG, font=font)
    ctx.y = y + 22 + margin_bottom


@register_block("habit_check_matrix")
def render_habit_check_matrix(ctx: RenderContext, block: dict) -> None:
    """7天打卡方阵。"""
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 6) * ctx.scale)
    name = str(block.get("name", "晨跑 5KM"))
    days = block.get("days") or [True, True, False, True, True, True, False]
    x = ctx.x_offset + margin_x
    y = ctx.y

    font = load_font("noto_serif_regular", int(9 * ctx.scale))
    ctx.draw.text((x, y), name, fill=EINK_FG, font=font)
    sx = x + 100
    for i, done in enumerate(days):
        bx = sx + i * 14
        fill = EINK_FG if done else None
        _draw_box(ctx.draw, (bx, y + 1, bx + 10, y + 11), outline=EINK_FG, fill=fill)
    ctx.y = y + 14 + margin_bottom


@register_block("countdown_flip_digit")
def render_countdown_flip_digit(ctx: RenderContext, block: dict) -> None:
    """翻页式倒计时单字格。"""
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 6) * ctx.scale)
    val = str(block.get("digit", "42"))
    unit = str(block.get("unit", "DAYS"))
    x = ctx.x_offset + margin_x
    y = ctx.y

    _draw_box(ctx.draw, (x, y, x + 36, y + 36), fill=EINK_FG)
    ctx.draw.line((x, y + 18, x + 36, y + 18), fill=EINK_BG, width=1)
    font_d = load_font("noto_serif_bold", int(18 * ctx.scale))
    tb = safe_font_bbox(font_d, val)
    ctx.draw.text((x + (36 - (tb[2]-tb[0]))//2, y + (36 - (tb[3]-tb[1]))//2 - tb[1]), val, fill=EINK_BG, font=font_d)
    font_u = load_font("noto_serif_regular", int(9 * ctx.scale))
    ctx.draw.text((x + 44, y + 12), unit, fill=EINK_FG, font=font_u)
    ctx.y = y + 38 + margin_bottom


@register_block("lunar_solar_strip")
def render_lunar_solar_strip(ctx: RenderContext, block: dict) -> None:
    """农历与节气横幅。"""
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 4) * ctx.scale)
    lunar = str(block.get("lunar", "七月廿五 · 白露"))
    x = ctx.x_offset + margin_x
    y = ctx.y

    font = load_font("noto_serif_regular", int(9 * ctx.scale))
    ctx.draw.text((x, y), lunar, fill=EINK_FG, font=font)
    ctx.y = y + 13 + margin_bottom


@register_block("week_agenda_row")
def render_week_agenda_row(ctx: RenderContext, block: dict) -> None:
    """单日日程排期行。"""
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 4) * ctx.scale)
    t = str(block.get("time", "14:30"))
    title = str(block.get("title", "系统架构复盘会"))
    x = ctx.x_offset + margin_x
    y = ctx.y

    font_b = load_font("noto_serif_bold", int(9 * ctx.scale))
    font_r = load_font("noto_serif_regular", int(9 * ctx.scale))
    ctx.draw.text((x, y), t, fill=EINK_FG, font=font_b)
    ctx.draw.text((x + 46, y), title, fill=EINK_FG, font=font_r)
    ctx.y = y + 13 + margin_bottom


@register_block("meeting_room_slot")
def render_meeting_room_slot(ctx: RenderContext, block: dict) -> None:
    """会议室预约时段条。"""
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 4) * ctx.scale)
    room = str(block.get("room", "Room A3"))
    status = str(block.get("status", "BUSY 14:00-15:00"))
    x = ctx.x_offset + margin_x
    y = ctx.y

    font = load_font("noto_serif_regular", int(8 * ctx.scale))
    text = f"[{room}] {status}"
    tb = safe_font_bbox(font, text)
    bw = (tb[2] - tb[0]) + 8
    _draw_box(ctx.draw, (x, y, x + bw, y + 12), outline=EINK_FG, width=1)
    ctx.draw.text((x + 4, y + 1), text, fill=EINK_FG, font=font)
    ctx.y = y + 14 + margin_bottom


@register_block("task_checkbox_item")
def render_task_checkbox_item(ctx: RenderContext, block: dict) -> None:
    """复选框待办条目。"""
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 4) * ctx.scale)
    done = bool(block.get("done", True))
    task = str(block.get("task", "完成墨水屏200组件测试与验收"))
    x = ctx.x_offset + margin_x
    y = ctx.y

    _draw_box(ctx.draw, (x, y + 1, x + 9, y + 10), outline=EINK_FG, fill=EINK_FG if done else None)
    font = load_font("noto_serif_regular", int(9 * ctx.scale))
    ctx.draw.text((x + 15, y), task, fill=EINK_FG, font=font)
    ctx.y = y + 13 + margin_bottom


@register_block("focus_duration_bar")
def render_focus_duration_bar(ctx: RenderContext, block: dict) -> None:
    """深度专注时长条。"""
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 4) * ctx.scale)
    hours = str(block.get("duration", "4.5h Focus"))
    x = ctx.x_offset + margin_x
    y = ctx.y

    font = load_font("noto_serif_bold", int(9 * ctx.scale))
    ctx.draw.text((x, y), f"DEEP WORK: {hours}", fill=EINK_FG, font=font)
    ctx.y = y + 13 + margin_bottom


@register_block("solar_term_badge")
def render_solar_term_badge(ctx: RenderContext, block: dict) -> None:
    """节气印章徽章。"""
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 4) * ctx.scale)
    term = str(block.get("term", "白露"))
    x = ctx.x_offset + margin_x
    y = ctx.y

    _draw_box(ctx.draw, (x, y, x + 24, y + 24), outline=EINK_FG, width=1)
    font = load_font("noto_serif_bold", int(9 * ctx.scale))
    ctx.draw.text((x + 3, y + 2), term[:1], fill=EINK_FG, font=font)
    ctx.draw.text((x + 3, y + 12), term[1:2], fill=EINK_FG, font=font)
    ctx.y = y + 26 + margin_bottom


@register_block("event_countdown_pill")
def render_event_countdown_pill(ctx: RenderContext, block: dict) -> None:
    """倒数纪念日小胶囊。"""
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 4) * ctx.scale)
    evt = str(block.get("event", "Next Release"))
    days = str(block.get("days", "12d"))
    x = ctx.x_offset + margin_x
    y = ctx.y

    font = load_font("noto_serif_regular", int(9 * ctx.scale))
    text = f"{evt}: {days}"
    tb = safe_font_bbox(font, text)
    bw = (tb[2] - tb[0]) + 8
    _draw_box(ctx.draw, (x, y, x + bw, y + 13), fill=EINK_FG)
    ctx.draw.text((x + 4, y + 1), text, fill=EINK_BG, font=font)
    ctx.y = y + 15 + margin_bottom


@register_block("day_progress_dots")
def render_day_progress_dots(ctx: RenderContext, block: dict) -> None:
    """一日24小时点阵走势。"""
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 4) * ctx.scale)
    cur_hour = int(block.get("hour", 16))
    x = ctx.x_offset + margin_x
    y = ctx.y

    for h in range(24):
        dx = x + h * 6
        fill = EINK_FG if h <= cur_hour else None
        ctx.draw.ellipse((dx, y + 2, dx + 3, y + 5), outline=EINK_FG, fill=fill)
    ctx.y = y + 9 + margin_bottom


@register_block("sleep_score_dial")
def render_sleep_score_dial(ctx: RenderContext, block: dict) -> None:
    """睡眠质量评分圆圈。"""
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 4) * ctx.scale)
    score = str(block.get("score", "88"))
    x = ctx.x_offset + margin_x + 14
    y = ctx.y + 14

    ctx.draw.ellipse((x - 12, y - 12, x + 12, y + 12), outline=EINK_FG, width=1)
    font = load_font("noto_serif_bold", int(8 * ctx.scale))
    tb = safe_font_bbox(font, score)
    ctx.draw.text((x - (tb[2]-tb[0])//2, y - (tb[3]-tb[1])//2 - tb[1]), score, fill=EINK_FG, font=font)
    font_lbl = load_font("noto_serif_regular", int(9 * ctx.scale))
    ctx.draw.text((x + 20, y - 6), "SLEEP SCORE", fill=EINK_FG, font=font_lbl)
    ctx.y = y + 16 + margin_bottom


@register_block("weekly_goal_tracker")
def render_weekly_goal_tracker(ctx: RenderContext, block: dict) -> None:
    """周目标达成进度条。"""
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 4) * ctx.scale)
    done = int(block.get("done", 4))
    total = int(block.get("total", 5))
    x = ctx.x_offset + margin_x
    y = ctx.y

    font = load_font("noto_serif_regular", int(9 * ctx.scale))
    ctx.draw.text((x, y), f"WEEKLY GOAL: {done}/{total}", fill=EINK_FG, font=font)
    ctx.y = y + 13 + margin_bottom


@register_block("time_zone_duo")
def render_time_zone_duo(ctx: RenderContext, block: dict) -> None:
    """双时区对照排版行。"""
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 4) * ctx.scale)
    tz1 = str(block.get("tz1", "BJS 16:30"))
    tz2 = str(block.get("tz2", "UTC 08:30"))
    x = ctx.x_offset + margin_x
    y = ctx.y

    font = load_font("noto_serif_bold", int(10 * ctx.scale))
    ctx.draw.text((x, y), f"{tz1}  |  {tz2}", fill=EINK_FG, font=font)
    ctx.y = y + 14 + margin_bottom
