"""
空间站过境与天文观测排版组件 (Space Station & Astrometry E-Ink Board Block)
提供航天遥测风格的硬核深空排版：过境窗口焦点卡片、轨道高度/速度遥测柱、焦点天文事件卡片。
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


@register_block("space_watch_board")
def render_space_watch_board(ctx: RenderContext, block: dict[str, Any]) -> None:
    scale = ctx.scale
    margin_x = int(block.get("margin_x", 8) * scale)
    avail_w = ctx.available_width - margin_x * 2

    font_banner_title = load_font("noto_serif_bold", max(11, int(12 * scale)))
    font_banner_val = load_font("inter_bold", max(12, int(13 * scale)))
    font_meta = load_font("inter_regular", max(8, int(9.5 * scale)))
    font_bold = load_font("inter_bold", max(9, int(10 * scale)))
    font_cjk_bold = load_font("noto_serif_bold", max(10, int(11 * scale)))
    font_cjk_reg = load_font("noto_serif_regular", max(8, int(9.5 * scale)))

    # 1. 顶部：过境观测焦点大卡片
    card_h = int(58 * scale)
    card_x = ctx.x_offset + margin_x
    card_y = ctx.y

    ctx.draw.rounded_rectangle(
        [card_x, card_y, card_x + avail_w, card_y + card_h],
        radius=4,
        outline=EINK_FG,
        width=1,
    )

    # 顶部微标行：[过境预报] 中国空间站 (天宫) · 亮度 -2.3 等
    target_name = str(ctx.get_field("target_name") or "中国空间站")
    brightness = str(ctx.get_field("brightness") or "-2.3 等")
    badge_text = "肉眼过境预报"
    b_bb = ctx.draw.textbbox((0, 0), badge_text, font=font_meta)
    bw = b_bb[2] - b_bb[0] + int(8 * scale)
    bh = int(16 * scale)

    # 反白黑底胶囊
    ctx.draw.rounded_rectangle(
        [card_x + int(4 * scale), card_y + int(4 * scale), card_x + int(4 * scale) + bw, card_y + int(4 * scale) + bh],
        radius=2,
        fill=EINK_FG,
    )
    ctx.draw.text(
        (card_x + int(8 * scale), card_y + int(4.5 * scale)),
        badge_text,
        fill=EINK_BG,
        font=font_meta,
    )

    ctx.draw.text(
        (card_x + int(8 * scale) + bw, card_y + int(4 * scale)),
        f"{target_name}  {brightness}",
        fill=EINK_FG,
        font=font_banner_title,
    )

    # 过境关键参数三联排
    pass_time = str(ctx.get_field("next_pass_time") or "今晚 20:38")
    pass_elev = str(ctx.get_field("next_pass_elevation") or "64°")
    pass_dir = str(ctx.get_field("pass_direction") or "西南 ➔ 东北")
    pass_dur = str(ctx.get_field("next_pass_duration") or "5 分 40 秒")

    row1_y = card_y + int(24 * scale)
    ctx.draw.text((card_x + int(8 * scale), row1_y), f"过境时刻: {pass_time}", fill=EINK_FG, font=font_banner_val)
    ctx.draw.text((card_x + int(150 * scale), row1_y), f"最大仰角: {pass_elev}", fill=EINK_FG, font=font_banner_val)

    row2_y = row1_y + int(16 * scale)
    ctx.draw.text((card_x + int(8 * scale), row2_y), f"运行航向: {pass_dir}   |   可见时长: {pass_dur}", fill=EINK_FG, font=font_meta)

    ctx.y = card_y + card_h + int(6 * scale)

    # 2. 中间：轨道遥测与在轨乘组 (两分栏)
    col_gap = int(6 * scale)
    col_w = (avail_w - col_gap) // 2
    box_h = int(48 * scale)

    # 左分栏：轨道遥测参数
    left_x = ctx.x_offset + margin_x
    ctx.draw.rounded_rectangle([left_x, ctx.y, left_x + col_w, ctx.y + box_h], radius=4, outline=EINK_FG, width=1)
    ctx.draw.text((left_x + int(6 * scale), ctx.y + int(4 * scale)), "ORBIT TELEMETRY 遥测", fill=EINK_FG, font=font_bold)

    alt = str(ctx.get_field("orbit_altitude") or "398.5 km")
    vel = str(ctx.get_field("orbit_velocity") or "7.68 km/s")
    inc = str(ctx.get_field("orbit_inclination") or "41.5°")
    ctx.draw.text((left_x + int(6 * scale), ctx.y + int(18 * scale)), f"轨道高度: {alt}", fill=EINK_FG, font=font_cjk_reg)
    ctx.draw.text((left_x + int(6 * scale), ctx.y + int(31 * scale)), f"速度: {vel} | 倾角: {inc}", fill=EINK_FG, font=font_cjk_reg)

    # 右分栏：天文速报
    right_x = left_x + col_w + col_gap
    ctx.draw.rounded_rectangle([right_x, ctx.y, right_x + col_w, ctx.y + box_h], radius=4, outline=EINK_FG, width=1)
    astro_title = str(ctx.get_field("astronomy_event_title") or "深空天文速报")
    astro_desc = str(ctx.get_field("astronomy_event_desc") or "黄昏肉眼可见行星与月亮相伴")
    ctx.draw.text((right_x + int(6 * scale), ctx.y + int(4 * scale)), astro_title[:14], fill=EINK_FG, font=font_cjk_bold)
    
    # 描述截断 2 行
    d_chars = max(10, int((col_w - int(12 * scale)) / (9 * scale)))
    ctx.draw.text((right_x + int(6 * scale), ctx.y + int(19 * scale)), astro_desc[:d_chars], fill=EINK_FG, font=font_cjk_reg)
    if len(astro_desc) > d_chars:
        ctx.draw.text((right_x + int(6 * scale), ctx.y + int(32 * scale)), astro_desc[d_chars:d_chars * 2], fill=EINK_FG, font=font_cjk_reg)

    ctx.y += box_h + int(6 * scale)

    # 3. 底部：乘组任务进度条
    crew_info = str(ctx.get_field("crew_info") or "载人航天飞行任务持续进行中")
    ctx.draw.text((ctx.x_offset + margin_x + int(4 * scale), ctx.y), f"★ {crew_info}", fill=EINK_FG, font=font_cjk_reg)
    ctx.y += int(14 * scale)
