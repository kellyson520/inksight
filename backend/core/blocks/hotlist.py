"""
全网热点高密度排版组件模块 (Hotlist Board E-Ink Layout Blocks)
包含三种精美现代墨水屏热榜呈现形态：
1. dense_grid: 双列高信息密度精选卡片看板（左右各 3-4 条，多达 6-8 条热搜，极大化利用屏幕）
2. editorial: 杂志级头条聚焦点刊（TOP 1 醒目大卡片 + TOP 2-5 次级排行）
3. classic: 精致胶囊排行单列流（圆角排行徽标 + 来源小标签 + 热度值）
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
    has_cjk,
    load_font,
    wrap_text,
)
from .context import RenderContext
from .registry import register_block
from .text import pick_cjk_font

logger = logging.getLogger(__name__)

_DEFAULT_RED = EINK_COLOR_NAME_MAP.get("red", 2)


def _draw_badge_pill(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    text: str,
    font,
    solid: bool = True,
    fill_color: int = EINK_FG,
    text_color: int = EINK_BG,
    pad_x: int = 4,
    pad_y: int = 1,
    radius: int = 3,
) -> tuple[int, int]:
    """绘制小巧的微型徽标或胶囊。返回 (width, height)。"""
    bbox = font.getbbox(text)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    w = tw + pad_x * 2
    h = max(th, 10) + pad_y * 2

    if solid:
        draw.rounded_rectangle([x, y, x + w, y + h], radius=radius, fill=fill_color)
        draw.text((x + pad_x - bbox[0], y + pad_y - bbox[1]), text, fill=text_color, font=font)
    else:
        draw.rounded_rectangle([x, y, x + w, y + h], radius=radius, outline=fill_color, width=1)
        draw.text((x + pad_x - bbox[0], y + pad_y - bbox[1]), text, fill=fill_color, font=font)

    return w, h


def _truncate_text_to_width(text: str, font, max_width: int) -> str:
    """如果文字超过 max_width，则智能截断并添加省略号。"""
    bbox = font.getbbox(text)
    if (bbox[2] - bbox[0]) <= max_width:
        return text
    ell = "..."
    ell_w = font.getbbox(ell)[2] - font.getbbox(ell)[0]
    target_w = max_width - ell_w
    if target_w <= 0:
        return ell
    cur = ""
    for ch in text:
        test = cur + ch
        if (font.getbbox(test)[2] - font.getbbox(test)[0]) > target_w:
            return cur + ell
        cur = test
    return cur + ell


def render_hotlist_board(ctx: RenderContext, block: dict[str, Any]) -> None:
    """渲染全网热榜核心排版看板（自动根据 content 中的 style 或 block.style 分发渲染）。"""
    items = ctx.get_field("items")
    if not isinstance(items, list) or not items:
        # 回退检查 item_1 ~ item_5
        items = []
        for i in range(1, 9):
            val = ctx.get_field(f"item_{i}")
            if val:
                items.append({
                    "rank": i,
                    "title": str(val).split(". ", 1)[-1] if ". " in str(val) else str(val),
                    "platform": "zhihu",
                    "platform_name": "热点",
                    "hot_value": "",
                    "is_top": i <= 3,
                })

    if not items:
        return

    # 获取当前渲染风格
    style = str(
        block.get("style")
        or ctx.get_field("style")
        or "dense_grid"
    ).lower()

    if style in ("dense_grid", "dense", "cards", "grid"):
        _render_dense_grid(ctx, block, items)
    elif style in ("editorial", "magazine", "headline"):
        _render_editorial(ctx, block, items)
    else:
        _render_classic(ctx, block, items)


def _render_dense_grid(ctx: RenderContext, block: dict[str, Any], items: list[dict[str, Any]]) -> None:
    """渲染双列高密度热榜（左右两列并排，每列 3 条，共 6 条精选热点）。"""
    scale = ctx.scale
    margin_x = int(block.get("margin_x", 10) * scale)
    margin_bottom = int(block.get("margin_bottom", 6) * scale)
    max_items = int(block.get("max_items", 6))

    display_items = items[:max_items]
    k = len(display_items)
    left_count = (k + 1) // 2
    left_items = display_items[:left_count]
    right_items = display_items[left_count:]

    avail_w = ctx.available_width - margin_x * 2
    gap_x = int(12 * scale)
    col_w = (avail_w - gap_x) // 2

    font_rank = load_font("roboto_bold", int(9 * scale))
    font_plat = load_font(pick_cjk_font("noto_serif_regular"), int(9 * scale))
    font_title = load_font(pick_cjk_font("noto_serif_regular"), int(11 * scale))
    font_hot = load_font("roboto_light", int(8 * scale))

    accent_color = _DEFAULT_RED if ctx.colors >= 3 else EINK_FG

    start_y = ctx.y
    max_col_h = 0

    # 左右两列分别排版
    for col_idx, col_items in enumerate([left_items, right_items]):
        col_x = ctx.x_offset + margin_x + col_idx * (col_w + gap_x)
        cur_y = start_y

        for it in col_items:
            rank = int(it.get("rank", 1))
            is_top = it.get("is_top", rank <= 3)
            title = str(it.get("title", "")).strip()
            plat_name = str(it.get("platform_name") or it.get("platform") or "热点")
            hot_val = str(it.get("hot_value", "")).strip()

            # 1. 绘制顶部信息行：[Rank] [来源] [热度]
            pill_fill = accent_color if (is_top and ctx.colors >= 3) else EINK_FG
            rank_str = f"{rank:02d}" if rank < 10 else str(rank)
            rw, rh = _draw_badge_pill(
                ctx.draw, col_x, cur_y, rank_str, font_rank,
                solid=is_top, fill_color=pill_fill, text_color=EINK_BG,
                pad_x=int(3 * scale), pad_y=int(1 * scale), radius=2,
            )

            # 平台徽标
            plat_tag = plat_name
            pw, ph = _draw_badge_pill(
                ctx.draw, col_x + rw + int(4 * scale), cur_y, plat_tag, font_plat,
                solid=False, fill_color=EINK_FG, text_color=EINK_FG,
                pad_x=int(3 * scale), pad_y=int(1 * scale), radius=2,
            )

            # 热度值（靠右）
            if hot_val:
                if any(x in hot_val for x in ("♪", "★", "🔥", "★")):
                    hot_str = hot_val
                else:
                    hot_str = f"🔥{hot_val}"
                hw = font_hot.getbbox(hot_str)[2] - font_hot.getbbox(hot_str)[0]
                if col_x + col_w - hw > col_x + rw + pw + int(10 * scale):
                    ctx.draw.text((col_x + col_w - hw, cur_y + int(1 * scale)), hot_str, fill=EINK_FG, font=font_hot)

            cur_y += max(rh, ph) + int(3 * scale)

            # 2. 绘制标题（最多折行两行，第二行加省略号）
            lines = wrap_text(title, font_title, col_w)
            if len(lines) > 2:
                lines = [lines[0], _truncate_text_to_width(lines[1] + lines[2], font_title, col_w)]
            elif len(lines) == 1:
                pass

            line_h = int(14 * scale)
            for ln in lines:
                ctx.draw.text((col_x, cur_y), ln, fill=EINK_FG, font=font_title)
                cur_y += line_h

            cur_y += int(2 * scale)

            # 3. 项与项之间轻量虚线分割
            draw_dashed_line(
                ctx.draw,
                (col_x, cur_y),
                (col_x + col_w, cur_y),
                fill=EINK_FG,
                width=1,
            )
            cur_y += int(5 * scale)

        col_h = cur_y - start_y
        if col_h > max_col_h:
            max_col_h = col_h

    ctx.y = start_y + max_col_h + margin_bottom


def _render_editorial(ctx: RenderContext, block: dict[str, Any], items: list[dict[str, Any]]) -> None:
    """渲染杂志级头条聚焦点刊风格（TOP 1 大卡片突出，下方 4 条精简列表）。"""
    scale = ctx.scale
    margin_x = int(block.get("margin_x", 12) * scale)
    margin_bottom = int(block.get("margin_bottom", 6) * scale)
    accent_color = _DEFAULT_RED if ctx.colors >= 3 else EINK_FG

    avail_w = ctx.available_width - margin_x * 2
    top_item = items[0]
    sub_items = items[1:5]

    font_banner = load_font(pick_cjk_font("noto_serif_bold"), int(10 * scale))
    font_hero_title = load_font(pick_cjk_font("noto_serif_bold"), int(14 * scale))
    font_rank = load_font("roboto_bold", int(10 * scale))
    font_sub_title = load_font(pick_cjk_font("noto_serif_regular"), int(12 * scale))
    font_meta = load_font(pick_cjk_font("noto_serif_regular"), int(9 * scale))

    # 1. 渲染 TOP 1 焦点大卡片
    card_x = ctx.x_offset + margin_x
    card_y = ctx.y
    card_pad = int(8 * scale)
    inner_w = avail_w - card_pad * 2

    hero_title = str(top_item.get("title", "")).strip()
    hero_plat = str(top_item.get("platform_name") or top_item.get("platform") or "今日头条")
    hero_hot = str(top_item.get("hot_value", "")).strip()

    # 计算大标题折行
    hero_lines = wrap_text(hero_title, font_hero_title, inner_w)
    if len(hero_lines) > 2:
        hero_lines = [hero_lines[0], _truncate_text_to_width(hero_lines[1] + hero_lines[2], font_hero_title, inner_w)]

    hero_h = card_pad * 2 + int(14 * scale) + len(hero_lines) * int(18 * scale) + int(4 * scale)
    ctx.draw.rounded_rectangle([card_x, card_y, card_x + avail_w, card_y + hero_h], radius=5, outline=EINK_FG, width=1)

    # 顶部焦点徽章行
    badge_w, badge_h = _draw_badge_pill(
        ctx.draw, card_x + card_pad, card_y + card_pad, "TOP 1 焦点头条", font_banner,
        solid=True, fill_color=accent_color, text_color=EINK_BG, pad_x=int(5 * scale), pad_y=int(1 * scale), radius=3,
    )
    _draw_badge_pill(
        ctx.draw, card_x + card_pad + badge_w + int(4 * scale), card_y + card_pad, hero_plat, font_meta,
        solid=False, fill_color=EINK_FG, text_color=EINK_FG, pad_x=int(4 * scale), pad_y=int(1 * scale), radius=2,
    )
    if hero_hot:
        hot_text = f"🔥 {hero_hot}"
        hw = font_meta.getbbox(hot_text)[2] - font_meta.getbbox(hot_text)[0]
        ctx.draw.text((card_x + avail_w - card_pad - hw, card_y + card_pad + int(1 * scale)), hot_text, fill=EINK_FG, font=font_meta)

    # 绘制大卡片主标题
    text_y = card_y + card_pad + badge_h + int(5 * scale)
    for ln in hero_lines:
        ctx.draw.text((card_x + card_pad, text_y), ln, fill=EINK_FG, font=font_hero_title)
        text_y += int(18 * scale)

    ctx.y = card_y + hero_h + int(8 * scale)

    # 2. 渲染次级热搜排行（2 ~ 5）
    for it in sub_items:
        rank = int(it.get("rank", 2))
        is_top = it.get("is_top", rank <= 3)
        title = str(it.get("title", "")).strip()
        plat_name = str(it.get("platform_name") or it.get("platform") or "热点")
        hot_val = str(it.get("hot_value", "")).strip()

        row_y = ctx.y
        pill_fill = accent_color if (is_top and ctx.colors >= 3) else EINK_FG
        rw, rh = _draw_badge_pill(
            ctx.draw, ctx.x_offset + margin_x, row_y, f"{rank:02d}", font_rank,
            solid=is_top, fill_color=pill_fill, text_color=EINK_BG, pad_x=int(3 * scale), pad_y=int(1 * scale), radius=2,
        )

        pw, ph = _draw_badge_pill(
            ctx.draw, ctx.x_offset + margin_x + rw + int(4 * scale), row_y, plat_name, font_meta,
            solid=False, fill_color=EINK_FG, text_color=EINK_FG, pad_x=int(3 * scale), pad_y=int(1 * scale), radius=2,
        )

        # 标题截断
        title_x = ctx.x_offset + margin_x + rw + pw + int(8 * scale)
        hot_w = (font_meta.getbbox(hot_val)[2] - font_meta.getbbox(hot_val)[0] + int(8 * scale)) if hot_val else 0
        max_t_w = ctx.available_width - margin_x * 2 - (rw + pw + int(8 * scale)) - hot_w
        short_t = _truncate_text_to_width(title, font_sub_title, max_t_w)
        ctx.draw.text((title_x, row_y - int(1 * scale)), short_t, fill=EINK_FG, font=font_sub_title)

        if hot_val:
            ctx.draw.text((ctx.x_offset + ctx.available_width - margin_x - hot_w + int(4 * scale), row_y + int(1 * scale)), hot_val, fill=EINK_FG, font=font_meta)

        ctx.y += max(rh, ph) + int(4 * scale)
        draw_dashed_line(
            ctx.draw,
            (ctx.x_offset + margin_x, ctx.y),
            (ctx.x_offset + ctx.available_width - margin_x, ctx.y),
            fill=EINK_FG, width=1,
        )
        ctx.y += int(5 * scale)

    ctx.y += margin_bottom


def _render_classic(ctx: RenderContext, block: dict[str, Any], items: list[dict[str, Any]]) -> None:
    """渲染精致胶囊排行流风格（单列 5 项，圆角徽章与清晰行距）。"""
    scale = ctx.scale
    margin_x = int(block.get("margin_x", 12) * scale)
    margin_bottom = int(block.get("margin_bottom", 6) * scale)
    accent_color = _DEFAULT_RED if ctx.colors >= 3 else EINK_FG

    font_rank = load_font("roboto_bold", int(11 * scale))
    font_plat = load_font(pick_cjk_font("noto_serif_regular"), int(10 * scale))
    font_title = load_font(pick_cjk_font("noto_serif_regular"), int(13 * scale))
    font_meta = load_font(pick_cjk_font("noto_serif_regular"), int(9 * scale))

    for it in items[:5]:
        rank = int(it.get("rank", 1))
        is_top = it.get("is_top", rank <= 3)
        title = str(it.get("title", "")).strip()
        plat_name = str(it.get("platform_name") or it.get("platform") or "热点")
        hot_val = str(it.get("hot_value", "")).strip()

        row_y = ctx.y
        pill_fill = accent_color if (is_top and ctx.colors >= 3) else EINK_FG
        rw, rh = _draw_badge_pill(
            ctx.draw, ctx.x_offset + margin_x, row_y, f"{rank:02d}", font_rank,
            solid=is_top, fill_color=pill_fill, text_color=EINK_BG, pad_x=int(4 * scale), pad_y=int(1 * scale), radius=3,
        )

        pw, ph = _draw_badge_pill(
            ctx.draw, ctx.x_offset + margin_x + rw + int(5 * scale), row_y, plat_name, font_plat,
            solid=False, fill_color=EINK_FG, text_color=EINK_FG, pad_x=int(4 * scale), pad_y=int(1 * scale), radius=2,
        )

        hot_w = (font_meta.getbbox(f"🔥 {hot_val}")[2] - font_meta.getbbox(f"🔥 {hot_val}")[0] + int(8 * scale)) if hot_val else 0
        title_x = ctx.x_offset + margin_x + rw + pw + int(10 * scale)
        max_t_w = ctx.available_width - margin_x * 2 - (rw + pw + int(10 * scale)) - hot_w

        short_t = _truncate_text_to_width(title, font_title, max_t_w)
        ctx.draw.text((title_x, row_y - int(1 * scale)), short_t, fill=EINK_FG, font=font_title)

        if hot_val:
            ctx.draw.text((ctx.x_offset + ctx.available_width - margin_x - hot_w + int(4 * scale), row_y + int(1 * scale)), f"🔥 {hot_val}", fill=EINK_FG, font=font_meta)

        ctx.y += max(rh, ph) + int(5 * scale)
        draw_dashed_line(
            ctx.draw,
            (ctx.x_offset + margin_x, ctx.y),
            (ctx.x_offset + ctx.available_width - margin_x, ctx.y),
            fill=EINK_FG, width=1,
        )
        ctx.y += int(6 * scale)

    ctx.y += margin_bottom


# 注册块渲染器
register_block("hotlist_board", render_hotlist_board)
