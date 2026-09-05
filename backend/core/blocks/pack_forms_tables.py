"""
InkSight 扩充排版组件库 8：表格、表单与结构容器组件 (Tables, Forms & Containers)
包含：
106. compact_table_row: 紧凑双栏数据行
107. matrix_key_value_grid: 四宫格键值矩阵卡
108. radio_choice_selector: 单选圆圈选项行
109. toggle_switch_row: 滑动开关模拟条目
110. slider_range_indicator: 模拟滑块区间刻度
111. nested_bullet_tree: 缩进树形层级清单
112. step_process_wizard: 横向 1-2-3 流程步骤条
113. collapsible_accordion_bar: 折叠抽屉标题栏
114. tab_strip_selector: 选项卡 Tab 切页栏
115. dialog_prompt_modal: 模拟弹出模态线框
116. toast_notification_chip: 微型浮动通知气泡
117. tooltip_annotation_box: 带下箭头的气泡提示框
118. pinned_note_card: 图钉便签贴纸卡
119. receipt_dashed_total: 小票下划线结算总额
120. ledger_debit_credit: 会计借贷记账对账行
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


@register_block("compact_table_row")
def render_compact_table_row(ctx: RenderContext, block: dict) -> None:
    """紧凑表格对齐行。"""
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 3) * ctx.scale)
    k = str(block.get("key", "Latency"))
    v = str(block.get("val", "12.4 ms"))
    x = ctx.x_offset + margin_x
    y = ctx.y
    w = ctx.available_width - margin_x * 2

    font = load_font("noto_serif_regular", int(9 * ctx.scale))
    ctx.draw.text((x, y), k, fill=EINK_FG, font=font)
    tb = safe_font_bbox(font, v)
    ctx.draw.text((x + w - (tb[2]-tb[0]), y), v, fill=EINK_FG, font=font)
    ctx.y = y + 13 + margin_bottom


@register_block("matrix_key_value_grid")
def render_matrix_key_value_grid(ctx: RenderContext, block: dict) -> None:
    """四宫格矩阵卡片。"""
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 6) * ctx.scale)
    x = ctx.x_offset + margin_x
    y = ctx.y
    w = ctx.available_width - margin_x * 2
    h = 32

    _draw_box(ctx.draw, (x, y, x + w, y + h), outline=EINK_FG, width=1)
    # 十字分割线
    ctx.draw.line((x + w // 2, y, x + w // 2, y + h), fill=EINK_FG, width=1)
    ctx.draw.line((x, y + h // 2, x + w, y + h // 2), fill=EINK_FG, width=1)
    font = load_font("noto_serif_regular", int(8 * ctx.scale))
    ctx.draw.text((x + 6, y + 2), "A: 98%", fill=EINK_FG, font=font)
    ctx.draw.text((x + w // 2 + 6, y + 2), "B: 12ms", fill=EINK_FG, font=font)
    ctx.draw.text((x + 6, y + h // 2 + 2), "C: OK", fill=EINK_FG, font=font)
    ctx.draw.text((x + w // 2 + 6, y + h // 2 + 2), "D: PASS", fill=EINK_FG, font=font)
    ctx.y = y + h + margin_bottom


@register_block("radio_choice_selector")
def render_radio_choice_selector(ctx: RenderContext, block: dict) -> None:
    """单选框选项行。"""
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 4) * ctx.scale)
    choice = str(block.get("choice", "Option 1: Enabled Mode"))
    selected = bool(block.get("selected", True))
    x = ctx.x_offset + margin_x
    y = ctx.y

    ctx.draw.ellipse((x, y + 1, x + 8, y + 9), outline=EINK_FG, width=1)
    if selected:
        ctx.draw.ellipse((x + 2, y + 3, x + 6, y + 7), fill=EINK_FG)
    font = load_font("noto_serif_regular", int(9 * ctx.scale))
    ctx.draw.text((x + 14, y), choice, fill=EINK_FG, font=font)
    ctx.y = y + 13 + margin_bottom


@register_block("toggle_switch_row")
def render_toggle_switch_row(ctx: RenderContext, block: dict) -> None:
    """滑动开关状态条。"""
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 4) * ctx.scale)
    label = str(block.get("label", "Dark Mode / Invert"))
    active = bool(block.get("active", True))
    x = ctx.x_offset + margin_x
    y = ctx.y
    w = ctx.available_width - margin_x * 2

    font = load_font("noto_serif_regular", int(9 * ctx.scale))
    ctx.draw.text((x, y), label, fill=EINK_FG, font=font)
    # 开关槽
    sw_x = x + w - 24
    _draw_box(ctx.draw, (sw_x, y, sw_x + 20, y + 10), outline=EINK_FG, width=1)
    if active:
        _draw_box(ctx.draw, (sw_x + 10, y + 1, sw_x + 19, y + 9), fill=EINK_FG)
    else:
        _draw_box(ctx.draw, (sw_x + 1, y + 1, sw_x + 10, y + 9), fill=EINK_FG)
    ctx.y = y + 14 + margin_bottom


@register_block("slider_range_indicator")
def render_slider_range_indicator(ctx: RenderContext, block: dict) -> None:
    """滑动刻度区间条。"""
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 4) * ctx.scale)
    pct = float(block.get("pct", 65.0))
    x = ctx.x_offset + margin_x
    y = ctx.y
    w = ctx.available_width - margin_x * 2

    ctx.draw.line((x, y + 5, x + w, y + 5), fill=EINK_FG, width=1)
    sx = int(x + w * (pct / 100.0))
    _draw_box(ctx.draw, (sx - 3, y + 1, sx + 3, y + 9), fill=EINK_FG)
    ctx.y = y + 12 + margin_bottom


@register_block("nested_bullet_tree")
def render_nested_bullet_tree(ctx: RenderContext, block: dict) -> None:
    """缩进树形层级清单。"""
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 4) * ctx.scale)
    parent = str(block.get("parent", "+ Architecture"))
    child = str(block.get("child", "  |- Cache Layer"))
    x = ctx.x_offset + margin_x
    y = ctx.y

    font = load_font("noto_serif_regular", int(9 * ctx.scale))
    ctx.draw.text((x, y), parent, fill=EINK_FG, font=font)
    ctx.draw.text((x, y + 11), child, fill=EINK_FG, font=font)
    ctx.y = y + 24 + margin_bottom


@register_block("step_process_wizard")
def render_step_process_wizard(ctx: RenderContext, block: dict) -> None:
    """步骤流程指示条 (1-2-3)。"""
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 4) * ctx.scale)
    step = int(block.get("step", 2))
    x = ctx.x_offset + margin_x
    y = ctx.y

    font = load_font("noto_serif_bold", int(8 * ctx.scale))
    for i in range(1, 4):
        bx = x + (i - 1) * 32
        fill = EINK_FG if i <= step else None
        text_color = EINK_BG if i <= step else EINK_FG
        _draw_box(ctx.draw, (bx, y, bx + 12, y + 12), outline=EINK_FG, fill=fill)
        ctx.draw.text((bx + 3, y + 1), str(i), fill=text_color, font=font)
        if i < 3:
            ctx.draw.line((bx + 14, y + 6, bx + 30, y + 6), fill=EINK_FG, width=1)
    ctx.y = y + 15 + margin_bottom


@register_block("collapsible_accordion_bar")
def render_collapsible_accordion_bar(ctx: RenderContext, block: dict) -> None:
    """折叠手风琴标题条。"""
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 4) * ctx.scale)
    title = str(block.get("title", "Advanced Configuration"))
    x = ctx.x_offset + margin_x
    y = ctx.y
    w = ctx.available_width - margin_x * 2

    _draw_box(ctx.draw, (x, y, x + w, y + 16), outline=EINK_FG, width=1)
    font = load_font("noto_serif_bold", int(9 * ctx.scale))
    ctx.draw.text((x + 6, y + 2), f"[-] {title}", fill=EINK_FG, font=font)
    ctx.y = y + 18 + margin_bottom


@register_block("tab_strip_selector")
def render_tab_strip_selector(ctx: RenderContext, block: dict) -> None:
    """选项卡切页栏。"""
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 4) * ctx.scale)
    tabs = block.get("tabs") or ["Overview", "Logs", "Metrics"]
    active_idx = int(block.get("active", 0))
    x = ctx.x_offset + margin_x
    y = ctx.y

    font = load_font("noto_serif_regular", int(9 * ctx.scale))
    cur_x = x
    for i, t in enumerate(tabs):
        tb = safe_font_bbox(font, t)
        tw = (tb[2] - tb[0]) + 12
        if i == active_idx:
            _draw_box(ctx.draw, (cur_x, y, cur_x + tw, y + 14), fill=EINK_FG)
            ctx.draw.text((cur_x + 6, y + 1), t, fill=EINK_BG, font=font)
        else:
            _draw_box(ctx.draw, (cur_x, y, cur_x + tw, y + 14), outline=EINK_FG, width=1)
            ctx.draw.text((cur_x + 6, y + 1), t, fill=EINK_FG, font=font)
        cur_x += tw + 4
    ctx.y = y + 16 + margin_bottom


@register_block("dialog_prompt_modal")
def render_dialog_prompt_modal(ctx: RenderContext, block: dict) -> None:
    """弹窗模态线框。"""
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 6) * ctx.scale)
    msg = str(block.get("msg", "Confirm deployment to production?"))
    x = ctx.x_offset + margin_x
    y = ctx.y
    w = ctx.available_width - margin_x * 2

    _draw_box(ctx.draw, (x, y, x + w, y + 26), outline=EINK_FG, width=1)
    font = load_font("noto_serif_regular", int(8 * ctx.scale))
    ctx.draw.text((x + 6, y + 3), msg, fill=EINK_FG, font=font)
    _draw_box(ctx.draw, (x + w - 46, y + 14, x + w - 6, y + 23), fill=EINK_FG)
    font_btn = load_font("noto_serif_bold", int(7 * ctx.scale))
    ctx.draw.text((x + w - 40, y + 15), "[YES]", fill=EINK_BG, font=font_btn)
    ctx.y = y + 28 + margin_bottom


@register_block("toast_notification_chip")
def render_toast_notification_chip(ctx: RenderContext, block: dict) -> None:
    """浮动通知气泡。"""
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 4) * ctx.scale)
    toast = str(block.get("toast", "Saved successfully"))
    x = ctx.x_offset + margin_x
    y = ctx.y

    font = load_font("noto_serif_regular", int(8 * ctx.scale))
    tb = safe_font_bbox(font, toast)
    bw = (tb[2] - tb[0]) + 16
    _draw_box(ctx.draw, (x, y, x + bw, y + 13), fill=EINK_FG)
    ctx.draw.text((x + 8, y + 1), toast, fill=EINK_BG, font=font)
    ctx.y = y + 15 + margin_bottom


@register_block("tooltip_annotation_box")
def render_tooltip_annotation_box(ctx: RenderContext, block: dict) -> None:
    """气泡提示框。"""
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 4) * ctx.scale)
    tip = str(block.get("tip", "Click to refresh realtime data"))
    x = ctx.x_offset + margin_x
    y = ctx.y

    font = load_font("noto_serif_regular", int(8 * ctx.scale))
    tb = safe_font_bbox(font, tip)
    bw = (tb[2] - tb[0]) + 10
    _draw_box(ctx.draw, (x, y, x + bw, y + 12), outline=EINK_FG, width=1)
    ctx.draw.text((x + 5, y + 1), tip, fill=EINK_FG, font=font)
    # 小三角箭头
    ctx.draw.line((x + 10, y + 12, x + 13, y + 15), fill=EINK_FG, width=1)
    ctx.draw.line((x + 16, y + 12, x + 13, y + 15), fill=EINK_FG, width=1)
    ctx.y = y + 17 + margin_bottom


@register_block("pinned_note_card")
def render_pinned_note_card(ctx: RenderContext, block: dict) -> None:
    """便签卡片。"""
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 6) * ctx.scale)
    note = str(block.get("note", "TODO: Review database backup schema."))
    x = ctx.x_offset + margin_x
    y = ctx.y
    w = ctx.available_width - margin_x * 2

    _draw_box(ctx.draw, (x, y, x + w, y + 24), outline=EINK_FG, width=1)
    # 图钉圆圈
    ctx.draw.ellipse((x + w // 2 - 3, y - 2, x + w // 2 + 3, y + 4), fill=EINK_FG)
    font = load_font("noto_serif_regular", int(8 * ctx.scale))
    ctx.draw.text((x + 6, y + 8), note, fill=EINK_FG, font=font)
    ctx.y = y + 26 + margin_bottom


@register_block("receipt_dashed_total")
def render_receipt_dashed_total(ctx: RenderContext, block: dict) -> None:
    """小票结算总额行。"""
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 4) * ctx.scale)
    total = str(block.get("total", "TOTAL: ¥348.00"))
    x = ctx.x_offset + margin_x
    y = ctx.y
    w = ctx.available_width - margin_x * 2

    # 顶部虚线
    for dx in range(0, w, 4):
        ctx.draw.line((x + dx, y, x + dx + 2, y), fill=EINK_FG, width=1)
    font = load_font("noto_serif_bold", int(10 * ctx.scale))
    ctx.draw.text((x, y + 3), total, fill=EINK_FG, font=font)
    ctx.y = y + 16 + margin_bottom


@register_block("ledger_debit_credit")
def render_ledger_debit_credit(ctx: RenderContext, block: dict) -> None:
    """会计记账对账行。"""
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 4) * ctx.scale)
    acc = str(block.get("acc", "Operating Exp"))
    dr = str(block.get("dr", "+5,000"))
    cr = str(block.get("cr", "-2,400"))
    x = ctx.x_offset + margin_x
    y = ctx.y

    font = load_font("noto_serif_regular", int(8 * ctx.scale))
    ctx.draw.text((x, y), f"{acc}: DR {dr} | CR {cr}", fill=EINK_FG, font=font)
    ctx.y = y + 12 + margin_bottom
