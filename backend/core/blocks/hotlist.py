"""
全网热点高密度排版组件模块 (Hotlist Board E-Ink Layout Blocks)
包含多种精美现代墨水屏热榜呈现形态：
1. dense_grid: 双列高信息密度精选卡片看板（左右各 4 条，完整展示前 8 条热搜，极大化利用屏幕）
2. cover_card: 图文展示精选热榜（TOP 1 焦点图文大卡片带封面 + TOP 2-8 双列精简榜单，图文并茂）
3. editorial: 杂志级头条聚焦点刊（TOP 1 醒目大卡片 + TOP 2-8 次级排行）
4. classic: 精致胶囊排行单列流（支持 5~8 项，圆角排行徽标 + 来源小标签 + 热度值）
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
    format_compact_number,
    has_cjk,
    load_font,
    wrap_text,
)
from .components import render_image
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
    fixed_h: int | None = None,
    min_w: int = 0,
) -> tuple[int, int]:
    """绘制小巧的微型徽标或胶囊，保证内部文字精准几何居中。返回 (width, height)。"""
    bbox = font.getbbox(text)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    w = max(tw + pad_x * 2, min_w)
    h = fixed_h if fixed_h is not None else (max(th, 10) + pad_y * 2)

    tx = x + (w - tw) // 2 - bbox[0]
    ty = y + (h - th) // 2 - bbox[1]

    if solid:
        draw.rounded_rectangle([x, y, x + w, y + h], radius=radius, fill=fill_color)
        draw.text((tx, ty), text, fill=text_color, font=font)
    else:
        draw.rounded_rectangle([x, y, x + w, y + h], radius=radius, outline=fill_color, width=1)
        draw.text((tx, ty), text, fill=fill_color, font=font)

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
        # 回退检查 item_1 ~ item_8
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

    if style in ("cover_card", "graphic", "image_text", "cover"):
        _render_cover_card(ctx, block, items)
    elif style in ("dense_grid", "dense", "cards", "grid"):
        _render_dense_grid(ctx, block, items)
    elif style in ("editorial", "magazine", "headline"):
        _render_editorial(ctx, block, items)
    else:
        _render_classic(ctx, block, items)


def _render_dense_grid(ctx: RenderContext, block: dict[str, Any], items: list[dict[str, Any]]) -> None:
    """渲染双列高密度热榜（行级对齐栅格，每行左右并列，左右列完全水平对齐，底线与字底绝对平整）。"""
    scale = ctx.scale
    margin_x = int(block.get("margin_x", 10) * scale)
    margin_bottom = int(block.get("margin_bottom", 6) * scale)
    max_items = int(block.get("max_items", 8))

    display_items = items[:max_items]
    k = len(display_items)
    left_count = (k + 1) // 2
    left_items = display_items[:left_count]
    right_items = display_items[left_count:]

    avail_w = ctx.available_width - margin_x * 2
    gap_x = int(12 * scale)
    col_w = (avail_w - gap_x) // 2
    col_left_x = ctx.x_offset + margin_x
    col_right_x = col_left_x + col_w + gap_x

    # 自适应字号与间距：若条目数多（如 7-8 条），使用微紧凑字号避免溢出屏幕
    is_dense_8 = k > 6
    font_rank = load_font("roboto_bold", int(8.5 * scale) if is_dense_8 else int(9 * scale))
    font_plat = load_font(pick_cjk_font("noto_serif_regular"), int(8.5 * scale) if is_dense_8 else int(9 * scale))
    font_title = load_font(pick_cjk_font("noto_serif_regular"), int(10 * scale) if is_dense_8 else int(11 * scale))
    font_hot = load_font("roboto_light", int(8 * scale))

    accent_color = _DEFAULT_RED if ctx.colors >= 3 else EINK_FG
    max_bottom = ctx.screen_h - ctx.footer_height - margin_bottom

    pill_h = int(13 * scale)
    line_h = int(12.5 * scale) if is_dense_8 else int(14 * scale)

    cur_y = ctx.y

    # 行级同步排版：左右对应成行，杜绝左右两列因折行差异导致的纵向微错位
    for r in range(left_count):
        it_l = left_items[r]
        it_r = right_items[r] if r < len(right_items) else None

        # 预先折行左右标题，统一求出该行的最高高度
        title_l = str(it_l.get("title", "")).strip()
        lines_l = wrap_text(title_l, font_title, col_w)
        if len(lines_l) > 2:
            lines_l = [lines_l[0], _truncate_text_to_width(lines_l[1] + lines_l[2], font_title, col_w)]

        lines_r = []
        if it_r:
            title_r = str(it_r.get("title", "")).strip()
            lines_r = wrap_text(title_r, font_title, col_w)
            if len(lines_r) > 2:
                lines_r = [lines_r[0], _truncate_text_to_width(lines_r[1] + lines_r[2], font_title, col_w)]

        content_h_l = pill_h + (int(2.5 * scale) if is_dense_8 else int(3.5 * scale)) + len(lines_l) * line_h
        content_h_r = (pill_h + (int(2.5 * scale) if is_dense_8 else int(3.5 * scale)) + len(lines_r) * line_h) if it_r else 0
        row_content_h = max(content_h_l, content_h_r)

        row_est_total = row_content_h + (int(4 * scale) if is_dense_8 else int(6 * scale))
        if cur_y + row_est_total > max_bottom:
            break

        # 绘制该行单元格的辅助函数
        def _draw_cell(col_x: int, it: dict[str, Any], lines: list[str]) -> None:
            rank = int(it.get("rank", 1))
            plat_name = str(it.get("platform_name") or it.get("platform") or "热点")
            hot_val = str(it.get("hot_value", "")).strip()

            pill_fill = accent_color if (rank == 1 and ctx.colors >= 3) else EINK_FG
            rank_str = f"{rank:02d}" if rank < 10 else str(rank)
            solid_badge = rank in (1, 2)
            rw, _ = _draw_badge_pill(
                ctx.draw, col_x, cur_y, rank_str, font_rank,
                solid=solid_badge, fill_color=pill_fill, text_color=EINK_BG if solid_badge else EINK_FG,
                pad_x=int(3 * scale), pad_y=int(1 * scale), radius=2,
                fixed_h=pill_h, min_w=int(17 * scale),
            )

            # 平台徽标（与 rank 徽标统一高度，严格垂直对齐）
            pw, _ = _draw_badge_pill(
                ctx.draw, col_x + rw + int(3 * scale), cur_y, plat_name, font_plat,
                solid=False, fill_color=EINK_FG, text_color=EINK_FG,
                pad_x=int(3 * scale), pad_y=int(1 * scale), radius=2,
                fixed_h=pill_h,
            )

            # 热度值（与徽标水平对齐）
            if hot_val:
                hot_str = hot_val if any(x in hot_val for x in ("♪", "★", "🔥")) else f"🔥{format_compact_number(hot_val)}"
                hot_bbox = font_hot.getbbox(hot_str)
                hw = hot_bbox[2] - hot_bbox[0]
                hth = hot_bbox[3] - hot_bbox[1]
                if col_x + col_w - hw > col_x + rw + pw + int(6 * scale):
                    hot_y = cur_y + (pill_h - hth) // 2 - hot_bbox[1]
                    ctx.draw.text((col_x + col_w - hw, hot_y), hot_str, fill=EINK_FG, font=font_hot)

            # 标题文字
            text_y = cur_y + pill_h + (int(2.5 * scale) if is_dense_8 else int(3.5 * scale))
            for ln in lines:
                ctx.draw.text((col_x, text_y), ln, fill=EINK_FG, font=font_title)
                text_y += line_h

        # 1. 绘制左列
        _draw_cell(col_left_x, it_l, lines_l)

        # 2. 绘制右列
        if it_r:
            _draw_cell(col_right_x, it_r, lines_r)

        cur_y += row_content_h + (int(1.5 * scale) if is_dense_8 else int(2.5 * scale))

        # 3. 左右列完全水平平齐的分割虚线
        draw_dashed_line(
            ctx.draw,
            (col_left_x, cur_y),
            (col_left_x + col_w, cur_y),
            fill=EINK_FG,
            width=1,
        )
        if it_r:
            draw_dashed_line(
                ctx.draw,
                (col_right_x, cur_y),
                (col_right_x + col_w, cur_y),
                fill=EINK_FG,
                width=1,
            )
        cur_y += int(3.5 * scale) if is_dense_8 else int(5 * scale)

    ctx.y = cur_y + margin_bottom


def _render_cover_card(ctx: RenderContext, block: dict[str, Any], items: list[dict[str, Any]]) -> None:
    """渲染图文展示精选热榜（TOP 1 焦点图文卡片带封面 + TOP 2-8 双列精简榜单，图文并茂）。"""
    scale = ctx.scale
    margin_x = int(block.get("margin_x", 10) * scale)
    margin_bottom = int(block.get("margin_bottom", 6) * scale)
    accent_color = _DEFAULT_RED if ctx.colors >= 3 else EINK_FG
    max_items = int(block.get("max_items", 8))

    avail_w = ctx.available_width - margin_x * 2
    top_item = items[0]
    sub_items = items[1:max_items]

    font_banner = load_font(pick_cjk_font("noto_serif_bold"), int(9 * scale))
    font_hero_title = load_font(pick_cjk_font("noto_serif_bold"), int(11.5 * scale))
    font_rank = load_font("roboto_bold", int(8.5 * scale))
    font_sub_title = load_font(pick_cjk_font("noto_serif_regular"), int(9.5 * scale))
    font_meta = load_font(pick_cjk_font("noto_serif_regular"), int(8 * scale))

    # 1. 顶部焦点图文卡片
    is_small_screen = ctx.screen_h <= 180
    card_x = ctx.x_offset + margin_x
    card_y = ctx.y
    card_h = int(54 * scale) if is_small_screen else int(82 * scale)
    card_pad = int(4 * scale) if is_small_screen else int(6 * scale)

    # 绘制外边框
    ctx.draw.rounded_rectangle([card_x, card_y, card_x + avail_w, card_y + card_h], radius=6 if not is_small_screen else 4, outline=EINK_FG, width=1)

    # 封面图尺寸 (16:9 / 4:3 比例)
    thumb_w = int(74 * scale) if is_small_screen else int(106 * scale)
    thumb_h = int(44 * scale) if is_small_screen else int(68 * scale)
    thumb_x = card_x + card_pad
    thumb_y = card_y + (card_h - thumb_h) // 2

    cover_val = top_item.get("image_data") or top_item.get("cover_url") or ctx.get_field("top_cover_url")
    rendered_image = False

    if cover_val:
        prev_img = ctx.content.get("__hotlist_top_cover")
        ctx.content["__hotlist_top_cover"] = cover_val
        try:
            render_image(ctx, {
                "field": "__hotlist_top_cover",
                "width": thumb_w,
                "height": thumb_h,
                "x": thumb_x,
                "y": thumb_y,
                "fit": "backdrop_blur",
            })
            rendered_image = True
        except Exception:
            rendered_image = False
        finally:
            if prev_img is None:
                ctx.content.pop("__hotlist_top_cover", None)
            else:
                ctx.content["__hotlist_top_cover"] = prev_img

    if not rendered_image:
        # 矢量墨水屏艺术降级缩略图
        ctx.draw.rounded_rectangle([thumb_x, thumb_y, thumb_x + thumb_w, thumb_y + thumb_h], radius=4, fill=EINK_FG)
        inner_m = int(2 * scale)
        ctx.draw.rounded_rectangle([thumb_x + inner_m, thumb_y + inner_m, thumb_x + thumb_w - inner_m, thumb_y + thumb_h - inner_m], radius=3, fill=EINK_BG)
        font_watermark = load_font("roboto_bold", int(20 * scale))
        ctx.draw.text((thumb_x + int(10 * scale), thumb_y + int(8 * scale)), "01", fill=EINK_FG, font=font_watermark)
        plat_icon_text = str(top_item.get("platform_name") or "HOT")
        ctx.draw.text((thumb_x + int(10 * scale), thumb_y + int(38 * scale)), f"★ {plat_icon_text}", fill=EINK_FG, font=font_meta)

    # 右侧文字排版
    text_x = thumb_x + thumb_w + int(8 * scale)
    text_w = card_x + avail_w - card_pad - text_x

    # 徽章栏：[TOP 1 头条] [平台] [🔥热度]
    pill_h = int(14 * scale) if not is_small_screen else int(12 * scale)
    rw, _ = _draw_badge_pill(
        ctx.draw, text_x, thumb_y, "TOP 1 头条", font_banner,
        solid=True, fill_color=accent_color, text_color=EINK_BG,
        pad_x=int(4 * scale), pad_y=int(1 * scale), radius=3, fixed_h=pill_h,
    )
    pw, _ = _draw_badge_pill(
        ctx.draw, text_x + rw + int(4 * scale), thumb_y, str(top_item.get("platform_name") or "热点"), font_meta,
        solid=False, fill_color=EINK_FG, text_color=EINK_FG,
        pad_x=int(3 * scale), pad_y=int(1 * scale), radius=2, fixed_h=pill_h,
    )
    hero_hot = str(top_item.get("hot_value", "")).strip()
    if hero_hot:
        hot_str = hero_hot if any(x in hero_hot for x in ("♪", "★", "🔥")) else f"🔥{format_compact_number(hero_hot)}"
        hot_bbox = font_meta.getbbox(hot_str)
        hw = hot_bbox[2] - hot_bbox[0]
        hth = hot_bbox[3] - hot_bbox[1]
        hot_x = card_x + avail_w - card_pad - hw
        if hot_x > text_x + rw + pw + int(6 * scale):
            hot_y = thumb_y + (pill_h - hth) // 2 - hot_bbox[1]
            ctx.draw.text((hot_x, hot_y), hot_str, fill=EINK_FG, font=font_meta)

    # 标题正文（最多折行3行）
    hero_title = str(top_item.get("title", "")).strip()
    title_lines = wrap_text(hero_title, font_hero_title, text_w)
    max_lines = 2 if is_small_screen else 3
    if len(title_lines) > max_lines:
        title_lines = title_lines[:max_lines - 1] + [_truncate_text_to_width("".join(title_lines[max_lines - 1:]), font_hero_title, text_w)]

    cur_text_y = thumb_y + pill_h + (int(3 * scale) if is_small_screen else int(5 * scale))
    line_spacing = int(12 * scale) if is_small_screen else int(15 * scale)
    for ln in title_lines:
        ctx.draw.text((text_x, cur_text_y), ln, fill=EINK_FG, font=font_hero_title)
        cur_text_y += line_spacing

    ctx.y = card_y + card_h + int(6 * scale)

    # 2. 下方次要热点排行（第 2 ~ 8 条，双列并排展示，每列水平对齐）
    if sub_items:
        gap_x = int(10 * scale)
        col_w = (avail_w - gap_x) // 2
        col_left_x = card_x
        col_right_x = card_x + col_w + gap_x

        sub_pill_h = int(13 * scale)
        sub_row_h = int(17 * scale)
        max_bottom = ctx.screen_h - ctx.footer_height - margin_bottom

        cur_y = ctx.y
        num_sub_rows = (len(sub_items) + 1) // 2

        for r in range(num_sub_rows):
            it_l = sub_items[r * 2]
            it_r = sub_items[r * 2 + 1] if (r * 2 + 1) < len(sub_items) else None

            if cur_y + sub_row_h > max_bottom:
                break

            def _draw_sub_cell(col_x: int, it: dict[str, Any]) -> None:
                rank = int(it.get("rank", 2))
                is_top = it.get("is_top", rank <= 3)
                title = str(it.get("title", "")).strip()
                plat_name = str(it.get("platform_name") or it.get("platform") or "热点")
                hot_val = str(it.get("hot_value", "")).strip()

                pill_fill = accent_color if (is_top and ctx.colors >= 3) else EINK_FG
                solid_badge = rank in (2, 3)

                rw, _ = _draw_badge_pill(
                    ctx.draw, col_x, cur_y, f"{rank:02d}", font_rank,
                    solid=solid_badge, fill_color=pill_fill, text_color=EINK_BG if solid_badge else EINK_FG,
                    pad_x=int(3 * scale), pad_y=int(1 * scale), radius=2,
                    fixed_h=sub_pill_h, min_w=int(17 * scale),
                )

                pw, _ = _draw_badge_pill(
                    ctx.draw, col_x + rw + int(3 * scale), cur_y, plat_name, font_meta,
                    solid=False, fill_color=EINK_FG, text_color=EINK_FG,
                    pad_x=int(2.5 * scale), pad_y=int(1 * scale), radius=2,
                    fixed_h=sub_pill_h,
                )

                hw = 0
                if hot_val:
                    hot_str = hot_val if any(x in hot_val for x in ("♪", "★", "🔥")) else f"🔥{format_compact_number(hot_val)}"
                    hot_bbox = font_meta.getbbox(hot_str)
                    hw = hot_bbox[2] - hot_bbox[0]
                    hth = hot_bbox[3] - hot_bbox[1]
                    hot_x = col_x + col_w - hw
                    if hot_x > col_x + rw + pw + int(6 * scale):
                        hot_y = cur_y + (sub_pill_h - hth) // 2 - hot_bbox[1]
                        ctx.draw.text((hot_x, hot_y), hot_str, fill=EINK_FG, font=font_meta)

                # 标题文字与徽标垂直居中对齐
                max_t_w = col_w - rw - pw - int(8 * scale) - (hw + int(4 * scale) if hw else 0)
                short_t = _truncate_text_to_width(title, font_sub_title, max_t_w)
                t_bbox = font_sub_title.getbbox(short_t)
                t_th = t_bbox[3] - t_bbox[1]
                t_y = cur_y + (sub_pill_h - t_th) // 2 - t_bbox[1]
                ctx.draw.text((col_x + rw + pw + int(5 * scale), t_y), short_t, fill=EINK_FG, font=font_sub_title)

            _draw_sub_cell(col_left_x, it_l)
            if it_r:
                _draw_sub_cell(col_right_x, it_r)

            cur_y += sub_row_h
            draw_dashed_line(ctx.draw, (col_left_x, cur_y), (col_left_x + col_w, cur_y), fill=EINK_FG, width=1)
            if it_r:
                draw_dashed_line(ctx.draw, (col_right_x, cur_y), (col_right_x + col_w, cur_y), fill=EINK_FG, width=1)
            cur_y += int(3 * scale)

        ctx.y = cur_y + margin_bottom


def _render_editorial(ctx: RenderContext, block: dict[str, Any], items: list[dict[str, Any]]) -> None:
    """渲染杂志级头条聚焦点刊风格（TOP 1 大卡片突出，下方 4 条精简列表）。"""
    scale = ctx.scale
    margin_x = int(block.get("margin_x", 12) * scale)
    margin_bottom = int(block.get("margin_bottom", 6) * scale)
    accent_color = _DEFAULT_RED if ctx.colors >= 3 else EINK_FG

    avail_w = ctx.available_width - margin_x * 2
    max_items = int(block.get("max_items", 8))
    top_item = items[0]
    sub_items = items[1:max_items]

    font_banner = load_font(pick_cjk_font("noto_serif_bold"), int(10 * scale))
    font_hero_title = load_font(pick_cjk_font("noto_serif_bold"), int(13 * scale))
    font_rank = load_font("roboto_bold", int(9 * scale) if len(sub_items) > 4 else int(10 * scale))
    font_sub_title = load_font(pick_cjk_font("noto_serif_regular"), int(10.5 * scale) if len(sub_items) > 4 else int(12 * scale))
    font_meta = load_font(pick_cjk_font("noto_serif_regular"), int(8.5 * scale) if len(sub_items) > 4 else int(9 * scale))

    # 1. 渲染 TOP 1 焦点大卡片
    card_x = ctx.x_offset + margin_x
    card_y = ctx.y
    card_pad = int(7 * scale)
    inner_w = avail_w - card_pad * 2

    hero_title = str(top_item.get("title", "")).strip()
    hero_plat = str(top_item.get("platform_name") or top_item.get("platform") or "今日头条")
    hero_hot = str(top_item.get("hot_value", "")).strip()

    # 计算大标题折行
    hero_lines = wrap_text(hero_title, font_hero_title, inner_w)
    if len(hero_lines) > 2:
        hero_lines = [hero_lines[0], _truncate_text_to_width(hero_lines[1] + hero_lines[2], font_hero_title, inner_w)]

    hero_h = card_pad * 2 + int(12 * scale) + len(hero_lines) * int(16 * scale) + int(4 * scale)
    ctx.draw.rounded_rectangle([card_x, card_y, card_x + avail_w, card_y + hero_h], radius=5, outline=EINK_FG, width=1)

    # 顶部焦点徽章行
    badge_h = int(14 * scale)
    badge_w, _ = _draw_badge_pill(
        ctx.draw, card_x + card_pad, card_y + card_pad, "TOP 1 焦点头条", font_banner,
        solid=True, fill_color=accent_color, text_color=EINK_BG,
        pad_x=int(4 * scale), pad_y=int(1 * scale), radius=3, fixed_h=badge_h,
    )
    _draw_badge_pill(
        ctx.draw, card_x + card_pad + badge_w + int(4 * scale), card_y + card_pad, hero_plat, font_meta,
        solid=False, fill_color=EINK_FG, text_color=EINK_FG,
        pad_x=int(3 * scale), pad_y=int(1 * scale), radius=2, fixed_h=badge_h,
    )
    if hero_hot:
        hot_text = f"🔥 {hero_hot}"
        hot_bbox = font_meta.getbbox(hot_text)
        hw = hot_bbox[2] - hot_bbox[0]
        hth = hot_bbox[3] - hot_bbox[1]
        hot_y = card_y + card_pad + (badge_h - hth) // 2 - hot_bbox[1]
        ctx.draw.text((card_x + avail_w - card_pad - hw, hot_y), hot_text, fill=EINK_FG, font=font_meta)

    # 绘制大卡片主标题
    text_y = card_y + card_pad + badge_h + int(4 * scale)
    for ln in hero_lines:
        ctx.draw.text((card_x + card_pad, text_y), ln, fill=EINK_FG, font=font_hero_title)
        text_y += int(16 * scale)

    ctx.y = card_y + hero_h + int(6 * scale)
    max_bottom = ctx.screen_h - ctx.footer_height - margin_bottom

    # 2. 渲染次级热搜排行（2 ~ 8）
    sub_pill_h = int(13 * scale)
    for it in sub_items:
        row_y = ctx.y
        if row_y + int(18 * scale) > max_bottom:
            break

        rank = int(it.get("rank", 2))
        is_top = it.get("is_top", rank <= 3)
        title = str(it.get("title", "")).strip()
        plat_name = str(it.get("platform_name") or it.get("platform") or "热点")
        hot_val = str(it.get("hot_value", "")).strip()

        pill_fill = accent_color if (is_top and ctx.colors >= 3) else EINK_FG
        rw, _ = _draw_badge_pill(
            ctx.draw, ctx.x_offset + margin_x, row_y, f"{rank:02d}", font_rank,
            solid=is_top, fill_color=pill_fill, text_color=EINK_BG,
            pad_x=int(3 * scale), pad_y=int(1 * scale), radius=2,
            fixed_h=sub_pill_h, min_w=int(17 * scale),
        )

        pw, _ = _draw_badge_pill(
            ctx.draw, ctx.x_offset + margin_x + rw + int(4 * scale), row_y, plat_name, font_meta,
            solid=False, fill_color=EINK_FG, text_color=EINK_FG,
            pad_x=int(3 * scale), pad_y=int(1 * scale), radius=2,
            fixed_h=sub_pill_h,
        )

        # 标题截断并垂直居中
        title_x = ctx.x_offset + margin_x + rw + pw + int(6 * scale)
        hot_w = 0
        h_bbox = None
        if hot_val:
            h_bbox = font_meta.getbbox(hot_val)
            hot_w = h_bbox[2] - h_bbox[0] + int(6 * scale)
        max_t_w = ctx.available_width - margin_x * 2 - (rw + pw + int(6 * scale)) - hot_w
        short_t = _truncate_text_to_width(title, font_sub_title, max_t_w)
        t_bbox = font_sub_title.getbbox(short_t)
        t_th = t_bbox[3] - t_bbox[1]
        t_y = row_y + (sub_pill_h - t_th) // 2 - t_bbox[1]
        ctx.draw.text((title_x, t_y), short_t, fill=EINK_FG, font=font_sub_title)

        if hot_val and h_bbox:
            h_th = h_bbox[3] - h_bbox[1]
            h_y = row_y + (sub_pill_h - h_th) // 2 - h_bbox[1]
            ctx.draw.text((ctx.x_offset + ctx.available_width - margin_x - hot_w + int(2 * scale), h_y), hot_val, fill=EINK_FG, font=font_meta)

        ctx.y += sub_pill_h + (int(2.5 * scale) if len(sub_items) > 4 else int(4 * scale))
        draw_dashed_line(
            ctx.draw,
            (ctx.x_offset + margin_x, ctx.y),
            (ctx.x_offset + ctx.available_width - margin_x, ctx.y),
            fill=EINK_FG, width=1,
        )
        ctx.y += int(3 * scale) if len(sub_items) > 4 else int(5 * scale)

    ctx.y += margin_bottom


def _render_classic(ctx: RenderContext, block: dict[str, Any], items: list[dict[str, Any]]) -> None:
    """渲染精致胶囊排行流风格（支持 5~8 项，圆角徽章与清晰行距，严格垂直中心轴对齐）。"""
    scale = ctx.scale
    margin_x = int(block.get("margin_x", 12) * scale)
    margin_bottom = int(block.get("margin_bottom", 6) * scale)
    accent_color = _DEFAULT_RED if ctx.colors >= 3 else EINK_FG
    max_items = int(block.get("max_items", 8))
    display_items = items[:max_items]
    max_bottom = ctx.screen_h - ctx.footer_height - margin_bottom

    is_compact = len(display_items) > 5
    font_rank = load_font("roboto_bold", int(9 * scale) if is_compact else int(11 * scale))
    font_plat = load_font(pick_cjk_font("noto_serif_regular"), int(8.5 * scale) if is_compact else int(10 * scale))
    font_title = load_font(pick_cjk_font("noto_serif_regular"), int(10.5 * scale) if is_compact else int(13 * scale))
    font_meta = load_font(pick_cjk_font("noto_serif_regular"), int(8.5 * scale) if is_compact else int(9 * scale))

    row_pill_h = int(13 * scale) if is_compact else int(15 * scale)

    for it in display_items:
        row_y = ctx.y
        if row_y + int(18 * scale) > max_bottom:
            break

        rank = int(it.get("rank", 1))
        is_top = it.get("is_top", rank <= 3)
        title = str(it.get("title", "")).strip()
        plat_name = str(it.get("platform_name") or it.get("platform") or "热点")
        hot_val = str(it.get("hot_value", "")).strip()

        pill_fill = accent_color if (rank == 1 and ctx.colors >= 3) else EINK_FG
        solid_badge = rank in (1, 2, 3) if is_compact else rank in (1, 2)
        rw, _ = _draw_badge_pill(
            ctx.draw, ctx.x_offset + margin_x, row_y, f"{rank:02d}", font_rank,
            solid=solid_badge, fill_color=pill_fill, text_color=EINK_BG if solid_badge else EINK_FG,
            pad_x=int(3 * scale) if is_compact else int(4 * scale),
            pad_y=int(1 * scale), radius=2 if is_compact else 3,
            fixed_h=row_pill_h, min_w=int(17 * scale) if is_compact else int(20 * scale),
        )

        pw, _ = _draw_badge_pill(
            ctx.draw, ctx.x_offset + margin_x + rw + int(4 * scale), row_y, plat_name, font_plat,
            solid=False, fill_color=EINK_FG, text_color=EINK_FG,
            pad_x=int(3 * scale) if is_compact else int(4 * scale),
            pad_y=int(1 * scale), radius=2,
            fixed_h=row_pill_h,
        )

        compact_hot = format_compact_number(hot_val) if hot_val else ""
        hot_label = hot_val if any(x in hot_val for x in ("♪", "★", "🔥")) else (f"🔥 {compact_hot}" if compact_hot else "")
        hot_w = 0
        h_bbox = None
        if hot_label:
            h_bbox = font_meta.getbbox(hot_label)
            hot_w = h_bbox[2] - h_bbox[0] + int(6 * scale)

        title_x = ctx.x_offset + margin_x + rw + pw + int(8 * scale)
        max_t_w = ctx.available_width - margin_x * 2 - (rw + pw + int(8 * scale)) - hot_w

        short_t = _truncate_text_to_width(title, font_title, max_t_w)
        t_bbox = font_title.getbbox(short_t)
        t_th = t_bbox[3] - t_bbox[1]
        t_y = row_y + (row_pill_h - t_th) // 2 - t_bbox[1]
        ctx.draw.text((title_x, t_y), short_t, fill=EINK_FG, font=font_title)

        if hot_label and h_bbox:
            h_th = h_bbox[3] - h_bbox[1]
            h_y = row_y + (row_pill_h - h_th) // 2 - h_bbox[1]
            ctx.draw.text((ctx.x_offset + ctx.available_width - margin_x - hot_w + int(2 * scale), h_y), hot_label, fill=EINK_FG, font=font_meta)

        ctx.y += row_pill_h + (int(2.5 * scale) if is_compact else int(4 * scale))
        draw_dashed_line(
            ctx.draw,
            (ctx.x_offset + margin_x, ctx.y),
            (ctx.x_offset + ctx.available_width - margin_x, ctx.y),
            fill=EINK_FG, width=1,
        )
        ctx.y += int(3 * scale) if is_compact else int(5 * scale)

    ctx.y += margin_bottom


# 注册块渲染器
register_block("hotlist_board", render_hotlist_board)
