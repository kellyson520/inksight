"""
全球外汇牌价与汇率监控墨水屏排版组件 (Currency Exchange Board Block)
提供现代微立体多币种网格对比看板，支持双列排列、涨跌幅徽章与换算参考。
"""
from __future__ import annotations

import logging
from typing import Any
from PIL import ImageDraw

from core.patterns.utils import (
    EINK_BG,
    EINK_FG,
    EINK_COLOR_NAME_MAP,
    draw_dashed_line,
    load_font,
)
from .context import RenderContext
from .registry import register_block

logger = logging.getLogger(__name__)


@register_block("currency_board")
def render_currency_board(ctx: RenderContext, block: dict[str, Any]) -> None:
    items = ctx.get_field(block.get("field", "items"))
    if not isinstance(items, list) or not items:
        return

    scale = ctx.scale
    margin_x = int(block.get("margin_x", 8) * scale)
    max_items = int(block.get("max_items", 6))
    render_items = items[:max_items]

    avail_w = ctx.available_width - margin_x * 2
    # 屏幕宽度大于 280 时采用精美双列排列，窄屏采用单列
    is_two_col = avail_w >= 280

    font_code = load_font("inter_bold", max(10, int(11 * scale)))
    font_name = load_font("noto_serif_regular", max(9, int(10 * scale)))
    font_rate = load_font("roboto_bold", max(12, int(13 * scale)))
    font_tip = load_font("inter_regular", max(8, int(9 * scale)))
    font_badge = load_font("inter_medium", max(8, int(8.5 * scale)))

    accent_color = EINK_COLOR_NAME_MAP.get("red", EINK_FG) if ctx.colors >= 3 else EINK_FG

    if is_two_col:
        gap_x = int(8 * scale)
        col_w = (avail_w - gap_x) // 2
        card_h = int(44 * scale)
        row_gap = int(6 * scale)

        for idx, item in enumerate(render_items):
            col_idx = idx % 2
            row_idx = idx // 2
            card_x = ctx.x_offset + margin_x + col_idx * (col_w + gap_x)
            card_y = ctx.y + row_idx * (card_h + row_gap)

            # 卡片外框（微圆角矩形）
            ctx.draw.rounded_rectangle(
                [card_x, card_y, card_x + col_w, card_y + card_h],
                radius=4,
                outline=EINK_FG,
                width=1,
            )

            # 1. 左侧：货币代码与中文名
            curr_code = str(item.get("currency", "")).upper()
            curr_name = str(item.get("name", ""))
            ctx.draw.text((card_x + int(6 * scale), card_y + int(4 * scale)), curr_code, fill=EINK_FG, font=font_code)
            ctx.draw.text((card_x + int(6 * scale), card_y + int(18 * scale)), curr_name, fill=EINK_FG, font=font_name)

            # 换算小贴士（最下方）
            tip_str = str(item.get("calc_tip", ""))
            if tip_str:
                ctx.draw.text((card_x + int(6 * scale), card_y + card_h - int(12 * scale)), tip_str, fill=EINK_FG, font=font_tip)

            # 2. 右侧：最新汇率数字
            rate_str = str(item.get("rate_str") or item.get("rate", ""))
            r_bb = ctx.draw.textbbox((0, 0), rate_str, font=font_rate)
            rw = r_bb[2] - r_bb[0]
            rate_x = card_x + col_w - rw - int(6 * scale)
            rate_y = card_y + int(4 * scale)
            ctx.draw.text((rate_x, rate_y), rate_str, fill=EINK_FG, font=font_rate)

            # 3. 涨跌幅微胶囊徽章
            change_str = str(item.get("change_str", "0.00%"))
            is_up = bool(item.get("is_up"))
            c_bb = ctx.draw.textbbox((0, 0), change_str, font=font_badge)
            cw = c_bb[2] - c_bb[0]
            ch = c_bb[3] - c_bb[1]
            bw = cw + int(6 * scale)
            bh = ch + int(2 * scale)
            badge_x = card_x + col_w - bw - int(6 * scale)
            badge_y = rate_y + int(15 * scale)

            badge_fill = accent_color if is_up and ctx.colors >= 3 else EINK_FG
            if is_up:
                # 实体反白小胶囊
                ctx.draw.rounded_rectangle([badge_x, badge_y, badge_x + bw, badge_y + bh], radius=2, fill=badge_fill)
                ctx.draw.text((badge_x + int(3 * scale), badge_y), change_str, fill=EINK_BG, font=font_badge)
            else:
                # 线框小胶囊
                ctx.draw.rounded_rectangle([badge_x, badge_y, badge_x + bw, badge_y + bh], radius=2, outline=EINK_FG, width=1)
                ctx.draw.text((badge_x + int(3 * scale), badge_y), change_str, fill=EINK_FG, font=font_badge)

        rows = (len(render_items) + 1) // 2
        ctx.y += rows * (card_h + row_gap)
    else:
        # 单列紧凑排版
        row_h = int(28 * scale)
        for idx, item in enumerate(render_items):
            cur_y = ctx.y + idx * row_h
            curr_code = str(item.get("currency", "")).upper()
            curr_name = str(item.get("name", ""))
            rate_str = str(item.get("rate_str") or item.get("rate", ""))
            change_str = str(item.get("change_str", "0.00%"))

            ctx.draw.text((ctx.x_offset + margin_x, cur_y + int(4 * scale)), f"{curr_code} {curr_name}", fill=EINK_FG, font=font_code)

            r_bb = ctx.draw.textbbox((0, 0), rate_str, font=font_rate)
            rw = r_bb[2] - r_bb[0]
            ctx.draw.text((ctx.x_offset + avail_w - rw - int(55 * scale), cur_y + int(3 * scale)), rate_str, fill=EINK_FG, font=font_rate)

            # 涨跌幅
            ctx.draw.text((ctx.x_offset + avail_w - int(48 * scale), cur_y + int(4 * scale)), change_str, fill=EINK_FG, font=font_badge)

            if idx < len(render_items) - 1:
                draw_dashed_line(
                    ctx.draw,
                    (ctx.x_offset + margin_x, cur_y + row_h - 1),
                    (ctx.x_offset + margin_x + avail_w, cur_y + row_h - 1),
                    fill=EINK_FG,
                    width=1,
                )
        ctx.y += len(render_items) * row_h
