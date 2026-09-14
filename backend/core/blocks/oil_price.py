"""
今日全国油价排版组件 (Oil Price E-Ink Board Block)
提供清晰醒目的油价行情对比卡片：包含调价预测倒计时焦点条、92#/95#/98#/0# 柴油四格网格牌价。
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
)
from .context import RenderContext
from .registry import register_block

logger = logging.getLogger(__name__)


@register_block("oil_price_board")
def render_oil_price_board(ctx: RenderContext, block: dict[str, Any]) -> None:
    scale = ctx.scale
    margin_x = int(block.get("margin_x", 8) * scale)
    avail_w = ctx.available_width - margin_x * 2

    font_label = load_font("inter_bold", max(11, int(12 * scale)))
    font_price = load_font("roboto_bold", max(16, int(18 * scale)))
    font_unit = load_font("noto_serif_regular", max(8, int(9 * scale)))
    font_trend = load_font("inter_medium", max(9, int(9.5 * scale)))
    font_banner = load_font("noto_serif_bold", max(10, int(11 * scale)))
    font_banner_sub = load_font("noto_serif_regular", max(9, int(9.5 * scale)))

    accent_color = EINK_COLOR_NAME_MAP.get("red", EINK_FG) if ctx.colors >= 3 else EINK_FG

    # 1. 顶部：调价预期横幅聚焦卡片
    banner_h = int(38 * scale)
    banner_x = ctx.x_offset + margin_x
    banner_y = ctx.y

    ctx.draw.rounded_rectangle(
        [banner_x, banner_y, banner_x + avail_w, banner_y + banner_h],
        radius=4,
        outline=EINK_FG,
        width=1,
    )

    # 倒计时徽标
    countdown_str = str(ctx.get_field("countdown_str") or "调价倒计时进行中")
    trend_badge = str(ctx.get_field("trend_badge") or "调价预测")
    trend_text = str(ctx.get_field("trend_text") or "预计本次调价平稳运行")
    is_drop = bool(ctx.get_field("is_drop"))

    # 左侧反色药丸徽章
    c_bb = ctx.draw.textbbox((0, 0), countdown_str, font=font_banner)
    cw = c_bb[2] - c_bb[0]
    pill_w = cw + int(8 * scale)
    pill_h = int(18 * scale)
    ctx.draw.rounded_rectangle(
        [banner_x + int(4 * scale), banner_y + int(4 * scale), banner_x + int(4 * scale) + pill_w, banner_y + int(4 * scale) + pill_h],
        radius=3,
        fill=EINK_FG,
    )
    ctx.draw.text(
        (banner_x + int(8 * scale), banner_y + int(5 * scale)),
        countdown_str,
        fill=EINK_BG,
        font=font_banner,
    )

    # 右侧趋势预测说明
    ctx.draw.text(
        (banner_x + int(8 * scale), banner_y + int(23 * scale)),
        trend_text,
        fill=EINK_FG,
        font=font_banner_sub,
    )

    ctx.y = banner_y + banner_h + int(8 * scale)

    # 2. 四格油品牌价网格 (2x2)
    grid_gap = int(6 * scale)
    col_w = (avail_w - grid_gap) // 2
    row_h = int(48 * scale)

    cards = [
        {"name": "92# 汽油", "price": ctx.get_field("gas_92") or "7.78", "change": ctx.get_field("change_92") or "-0.12"},
        {"name": "95# 汽油", "price": ctx.get_field("gas_95") or "8.35", "change": ctx.get_field("change_95") or "-0.13"},
        {"name": "98# 汽油", "price": ctx.get_field("gas_98") or "9.42", "change": ctx.get_field("change_98") or "-0.15"},
        {"name": "0# 柴油", "price": ctx.get_field("diesel_0") or "7.41", "change": ctx.get_field("change_diesel") or "-0.12"},
    ]

    for idx, card in enumerate(cards):
        col = idx % 2
        row = idx // 2
        c_x = ctx.x_offset + margin_x + col * (col_w + grid_gap)
        c_y = ctx.y + row * (row_h + grid_gap)

        # 卡片边框
        ctx.draw.rounded_rectangle(
            [c_x, c_y, c_x + col_w, c_y + row_h],
            radius=4,
            outline=EINK_FG,
            width=1,
        )

        # 标号名称
        ctx.draw.text((c_x + int(6 * scale), c_y + int(5 * scale)), card["name"], fill=EINK_FG, font=font_label)

        # 价格与单位
        p_str = f"¥{card['price']}"
        p_bb = ctx.draw.textbbox((0, 0), p_str, font=font_price)
        pw = p_bb[2] - p_bb[0]
        ctx.draw.text((c_x + int(6 * scale), c_y + int(22 * scale)), p_str, fill=EINK_FG, font=font_price)

        ctx.draw.text((c_x + int(8 * scale) + pw, c_y + int(28 * scale)), "元/升", fill=EINK_FG, font=font_unit)

        # 预测变动小徽章（右上角）
        chg_str = str(card["change"])
        if chg_str and chg_str != "0.00":
            chg_text = f"↓{chg_str.lstrip('-')}" if chg_str.startswith("-") else f"↑{chg_str.lstrip('+')}"
            chg_bb = ctx.draw.textbbox((0, 0), chg_text, font=font_trend)
            cw = chg_bb[2] - chg_bb[0]
            bw = cw + int(6 * scale)
            bh = int(14 * scale)
            bx = c_x + col_w - bw - int(5 * scale)
            by = c_y + int(5 * scale)

            if is_drop:
                ctx.draw.rounded_rectangle([bx, by, bx + bw, by + bh], radius=2, fill=EINK_FG)
                ctx.draw.text((bx + int(3 * scale), by + int(1 * scale)), chg_text, fill=EINK_BG, font=font_trend)
            else:
                ctx.draw.rounded_rectangle([bx, by, bx + bw, by + bh], radius=2, outline=accent_color, width=1)
                ctx.draw.text((bx + int(3 * scale), by + int(1 * scale)), chg_text, fill=accent_color, font=font_trend)

    ctx.y += 2 * (row_h + grid_gap)
