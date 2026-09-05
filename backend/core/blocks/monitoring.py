"""
监控变动与事件通报排版组件模块 (Monitoring & Event Notification Blocks)
提供专为墨水屏设计的告警告示框、前值现值对比卡片与时间线事件卡片：
1. alert_callout: 告警与变动告示条/横幅
2. change_diff_card: 变动前后差分对比卡片 (Prev vs New Snippet)
3. timeline_event: 时间轴事件节点
【规范约束】：严禁 Emoji。
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


def render_alert_callout(ctx: RenderContext, block: dict[str, Any]) -> None:
    """渲染醒目的通报告示条/横幅。"""
    title = block.get("title") or ctx.resolve(block.get("title_template", "事件通报"))
    level = block.get("level", "warning")
    tag = block.get("tag", "NOTICE")
    margin_x = int(block.get("margin_x", 12) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 6) * ctx.scale)
    h = int(block.get("height", 32) * ctx.scale)

    x1 = ctx.x_offset + margin_x
    x2 = ctx.x_offset + ctx.available_width - margin_x
    y1 = ctx.y
    y2 = y1 + h

    # 4色/3色模式下，高优先级可采用强调色
    is_alert = level in ("danger", "warning", "critical")
    accent_color = _RED_COLOR if (is_alert and ctx.colors >= 3) else EINK_FG

    # 绘制外框与左侧粗指示色块
    _draw_rounded_rect(ctx.draw, (x1, y1, x2, y2), radius=4, outline=accent_color, width=2)
    # 左侧侧边色带 (宽度 6px)
    ctx.draw.rectangle((x1, y1 + 2, x1 + 6, y2 - 2), fill=accent_color)

    # 绘制 Tag 徽章
    tag_font_size = int(9 * ctx.scale)
    tag_font = load_font("noto_serif_bold", tag_font_size)
    tag_bbox = safe_font_bbox(tag_font, tag)
    tag_w = tag_bbox[2] - tag_bbox[0] + 8
    tag_h = tag_font_size + 4
    tag_x = x1 + 14
    tag_y = y1 + (h - tag_h) // 2

    _draw_rounded_rect(ctx.draw, (tag_x, tag_y, tag_x + tag_w, tag_y + tag_h), radius=2, fill=accent_color)
    ctx.draw.text((tag_x + 4, tag_y + 2), tag, fill=EINK_BG, font=tag_font)

    # 绘制标题文本
    title_font_size = int(12 * ctx.scale)
    title_font = load_font("noto_serif_bold", title_font_size)
    ctx.draw.text((tag_x + tag_w + 8, y1 + (h - title_font_size) // 2 - 1), title, fill=EINK_FG, font=title_font)

    ctx.y = y2 + margin_bottom


def render_change_diff_card(ctx: RenderContext, block: dict[str, Any]) -> None:
    """渲染前值与现值差分对比卡片。"""
    margin_x = int(block.get("margin_x", 12) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 6) * ctx.scale)

    prev_field = block.get("prev_field", "prev_snippet")
    new_field = block.get("new_field", "new_snippet")

    prev_text = str(ctx.get_field(prev_field) or "")
    new_text = str(ctx.get_field(new_field) or "")

    x1 = ctx.x_offset + margin_x
    x2 = ctx.x_offset + ctx.available_width - margin_x
    card_w = x2 - x1

    # 文本折行
    font_size = int(11 * ctx.scale)
    font = load_font("noto_serif_regular", font_size)
    bold_font = load_font("noto_serif_bold", font_size)
    label_font = load_font("noto_serif_bold", int(9 * ctx.scale))

    prev_lines = wrap_text(prev_text, font, card_w - 24)[:2] or ["暂无前置记录"]
    new_lines = wrap_text(new_text, bold_font, card_w - 24)[:3] or ["检测到新变更"]

    line_h = font_size + 4
    prev_box_h = len(prev_lines) * line_h + 16
    new_box_h = len(new_lines) * line_h + 16
    total_card_h = prev_box_h + new_box_h + 8

    y1 = ctx.y

    # 1. 绘制前值卡片 (细虚线/弱化边框)
    _draw_rounded_rect(ctx.draw, (x1, y1, x2, y1 + prev_box_h), radius=3, outline=EINK_FG, width=1)
    ctx.draw.text((x1 + 8, y1 + 3), "PREV", fill=EINK_FG, font=label_font)
    cur_y = y1 + 14
    for line in prev_lines:
        ctx.draw.text((x1 + 8, cur_y), line, fill=EINK_FG, font=font)
        cur_y += line_h

    # 2. 绘制现值卡片 (高亮加粗框)
    ny1 = y1 + prev_box_h + 4
    ny2 = ny1 + new_box_h
    accent_color = _RED_COLOR if ctx.colors >= 3 else EINK_FG

    _draw_rounded_rect(ctx.draw, (x1, ny1, x2, ny2), radius=3, outline=accent_color, width=2)
    # NEW 标签
    _draw_rounded_rect(ctx.draw, (x1 + 6, ny1 + 3, x1 + 36, ny1 + 15), radius=2, fill=accent_color)
    ctx.draw.text((x1 + 9, ny1 + 4), "NEW", fill=EINK_BG, font=label_font)

    n_cur_y = ny1 + 16
    for line in new_lines:
        ctx.draw.text((x1 + 8, n_cur_y), line, fill=EINK_FG, font=bold_font)
        n_cur_y += line_h

    ctx.y = ny2 + margin_bottom


def render_timeline_event(ctx: RenderContext, block: dict[str, Any]) -> None:
    """渲染时间线事件卡片。"""
    time_str = block.get("time") or ctx.resolve(block.get("time_template", ""))
    content = block.get("content") or ctx.resolve(block.get("content_template", ""))
    status = block.get("status", "info")
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 4) * ctx.scale)

    x1 = ctx.x_offset + margin_x
    x2 = ctx.x_offset + ctx.available_width - margin_x
    y1 = ctx.y

    dot_r = int(3 * ctx.scale)
    dot_x = x1 + dot_r + 2
    dot_y = y1 + int(7 * ctx.scale)

    accent_color = _RED_COLOR if (status in ("warning", "error") and ctx.colors >= 3) else EINK_FG

    # 绘制时间线圆点
    ctx.draw.ellipse((dot_x - dot_r, dot_y - dot_r, dot_x + dot_r, dot_y + dot_r), fill=accent_color)

    font_size = int(11 * ctx.scale)
    bold_font = load_font("noto_serif_bold", font_size)
    reg_font = load_font("noto_serif_regular", font_size)

    text_x = dot_x + dot_r + 8
    if time_str:
        ctx.draw.text((text_x, y1), str(time_str), fill=accent_color, font=bold_font)
        tb = safe_font_bbox(bold_font, str(time_str))
        tw = tb[2] - tb[0] + 8
    else:
        tw = 0

    ctx.draw.text((text_x + tw, y1), str(content), fill=EINK_FG, font=reg_font)
    ctx.y = y1 + font_size + 6 + margin_bottom


# 注册排版块
register_block("alert_callout", render_alert_callout)
register_block("change_diff_card", render_change_diff_card)
register_block("timeline_event", render_timeline_event)
