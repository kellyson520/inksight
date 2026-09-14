"""Compact recommendation list/card renderer for external media modes."""
from __future__ import annotations
from PIL import ImageDraw
from .context import RenderContext
from .registry import register_block
from .text import pick_cjk_font
from .components import render_image
from ..patterns.utils import (
    load_font,
    EINK_FG,
    EINK_BG,
    EINK_COLOR_NAME_MAP,
    draw_dashed_line,
)


@register_block("recommendation")
def render_recommendation(ctx: RenderContext, block: dict) -> None:
    items = ctx.get_field(block.get("field", "items"))
    if not isinstance(items, list): return
    style = str(ctx.get_field(block.get("style_field", "layout_style")) or "ranking")
    card_layout = str(block.get("card_layout") or "top_image")
    max_items = int(block.get("max_items", 5))
    font_size = int(block.get("font_size", 10) * ctx.scale)
    font = load_font("noto_serif_regular", font_size)
    bold = load_font("noto_serif_bold", font_size)
    small_font = load_font("noto_serif_light", max(9, int(font_size * 0.88)))
    y = ctx.y
    items_to_render = items[:1] if style == "cover_card" else items[:max_items]
    for index, item in enumerate(items_to_render, 1):
        if not isinstance(item, dict): continue
        title = str(item.get("title", "推荐")).strip()
        subtitle = str(item.get("subtitle", "")).strip()
        description = str(item.get("description") or "").strip()
        rank = str(item.get("rank_label") or f"NO.{index}")
        if style == "cover_card":
            image_data = item.get("image_data")
            image_url = str(item.get("thumbnail_url") or item.get("cover_url") or "").strip()
            fallback_image = item.get("fallback_image")
            max_allowed = max(40, ctx.screen_h - ctx.footer_height - y - int(4 * ctx.scale))
            card_h_prop = int(block.get("card_height", 0) * ctx.scale)
            if card_h_prop > 0:
                card_height = min(card_h_prop, max_allowed)
            else:
                card_height = max_allowed

            if card_layout == "left_text_right_image" and ctx.available_width >= 220:
                # ── 横向分栏：左文右图 ──
                # 右侧图片区域宽：按 35% 分配，留边距
                img_w = max(60, min(140, int((ctx.available_width - int(24 * ctx.scale)) * 0.35)))
                img_h = max(30, card_height - int(6 * ctx.scale))
                img_x = ctx.x_offset + ctx.available_width - img_w - int(10 * ctx.scale)
                img_y = y + int(2 * ctx.scale)

                if image_data is not None or image_url:
                    prev_img = ctx.content.get("__recommendation_image")
                    ctx.content["__recommendation_image"] = image_data if image_data is not None else image_url
                    render_image(ctx, {
                        "field": "__recommendation_image",
                        "width": img_w,
                        "height": img_h,
                        "x": img_x,
                        "y": img_y,
                        "fit": "contain",
                    })
                    if prev_img is None:
                        ctx.content.pop("__recommendation_image", None)
                    else:
                        ctx.content["__recommendation_image"] = prev_img

                # 左侧文字区域
                left_x = ctx.x_offset + int(10 * ctx.scale)
                left_w = img_x - left_x - int(12 * ctx.scale)
                cur_y = y + int(2 * ctx.scale)

                # 1. 榜单徽章与书名
                badge_title = f"{rank}  {title}"
                chars_per_line = max(6, int(left_w / (font_size * 0.95)))
                ctx.draw.text((left_x, cur_y), badge_title[:chars_per_line], fill=EINK_FG, font=bold)
                cur_y += font_size + int(6 * ctx.scale)

                # 2. 作者与分类
                if subtitle and cur_y + font_size < y + card_height - 10:
                    ctx.draw.text((left_x, cur_y), subtitle[:chars_per_line + 2], fill=EINK_FG, font=font)
                    cur_y += font_size + int(6 * ctx.scale)

                # 3. 简介描述（自动折行，最多 3~4 行）
                if description and cur_y < y + card_height - 12:
                    desc_chars_per_line = max(8, int(left_w / (font_size * 0.85)))
                    desc_lines = []
                    for chunk_idx in range(0, len(description), desc_chars_per_line):
                        desc_lines.append(description[chunk_idx:chunk_idx + desc_chars_per_line])
                        if len(desc_lines) >= 3:
                            break
                    for dl in desc_lines:
                        if cur_y + font_size > y + card_height - 4:
                            break
                        ctx.draw.text((left_x, cur_y), dl, fill=EINK_FG, font=small_font)
                        cur_y += int(font_size * 0.95) + int(3 * ctx.scale)

                y += card_height + int(2 * ctx.scale)
            else:
                # ── 纵向布局：上图下文（视频/插画全幅精美卡片） ──
                duration = str(item.get("duration") or "").strip()
                views = str(item.get("views_label") or "").strip()
                rating = str(item.get("rating_label") or "").strip()

                # 下方信息栏预留高度：若有视频标签（时长/播放量/好评），预留两行高度；否则预留单行高度
                has_video_meta = bool(duration or views or rating)
                text_block_h = (font_size * 2 + int(10 * ctx.scale)) if has_video_meta else (font_size + int(4 * ctx.scale))
                img_h = max(16, card_height - text_block_h - int(2 * ctx.scale))

                if image_data is not None or image_url or fallback_image is not None:
                    previous_image = ctx.content.get("__recommendation_image")
                    previous_fallback = ctx.content.get("__recommendation_fallback")
                    # 若存在优先远程 url 则由 media_fetcher 抓取，抓取失败则回退到 fallback_image
                    ctx.content["__recommendation_image"] = image_data if image_data is not None else (image_url or fallback_image)
                    if fallback_image is not None:
                        ctx.content["__recommendation_fallback"] = fallback_image
                    render_image(ctx, {
                        "field": "__recommendation_image",
                        "fallback_field": "__recommendation_fallback",
                        "width": max(20, ctx.available_width - int(20 * ctx.scale)),
                        "height": img_h,
                        "x": ctx.x_offset + int(10 * ctx.scale),
                        "y": y,
                        "fit": "contain",
                    })
                    if previous_image is None:
                        ctx.content.pop("__recommendation_image", None)
                    else:
                        ctx.content["__recommendation_image"] = previous_image
                    if previous_fallback is None:
                        ctx.content.pop("__recommendation_fallback", None)
                    else:
                        ctx.content["__recommendation_fallback"] = previous_fallback

                # 底部文字排版
                content_x = ctx.x_offset + int(10 * ctx.scale)
                max_chars = max(10, int((ctx.available_width - int(20 * ctx.scale)) / (font_size * 0.72)))
                line = f"{rank}  {title}"
                if subtitle and len(line) < 30 and ctx.available_width > 240:
                    line += f" · {subtitle}"

                if has_video_meta:
                    # 第一行：标题
                    title_y = y + card_height - text_block_h + int(2 * ctx.scale)
                    ctx.draw.text((content_x, title_y), line[:max_chars], fill=EINK_FG, font=bold)

                    # 第二行：视频元数据胶囊标签（时长、播放量、好评率）
                    meta_y = title_y + font_size + int(4 * ctx.scale)
                    meta_badges = []
                    if duration:
                        meta_badges.append(f"⏱ {duration}")
                    if views:
                        meta_badges.append(f"▶ {views}播放")
                    if rating:
                        meta_badges.append(f"★ {rating}好评")
                    meta_line = "   ".join(meta_badges)
                    ctx.draw.text((content_x, meta_y), meta_line[:max_chars + 6], fill=EINK_FG, font=small_font)
                else:
                    text_y = y + card_height - font_size - int(2 * ctx.scale)
                    ctx.draw.text((content_x, text_y), line[:max_chars], fill=EINK_FG, font=bold)

                y += card_height + int(2 * ctx.scale)
        else:
            # ── 精致现代墨水屏排行榜排版 ──
            available_h = max(30, ctx.screen_h - ctx.footer_height - ctx.y - int(4 * ctx.scale))
            rem_count = max(1, len(items_to_render) - index + 1)
            row_h = max(int(font_size * 1.8), min(int(36 * ctx.scale), available_h // rem_count))

            x_left = ctx.x_offset + int(8 * ctx.scale)
            badge_size = max(13, int(font_size * 1.25))
            badge_y = y + (row_h - badge_size) // 2

            # 1. 排名徽章 (前三名高对比度微立体/反白突出)
            badge_color = EINK_FG
            badge_text_color = EINK_BG
            is_solid = True

            if index == 1:
                if ctx.colors >= 3:
                    badge_color = EINK_COLOR_NAME_MAP.get("red", EINK_FG)
                is_solid = True
            elif index == 2:
                badge_color = EINK_FG
                is_solid = True
            elif index == 3:
                badge_color = EINK_FG
                is_solid = False
                badge_text_color = EINK_FG
            else:
                badge_color = EINK_FG
                is_solid = False
                badge_text_color = EINK_FG

            if is_solid:
                ctx.draw.rounded_rectangle(
                    [x_left, badge_y, x_left + badge_size, badge_y + badge_size],
                    radius=3,
                    fill=badge_color,
                )
            else:
                ctx.draw.rounded_rectangle(
                    [x_left, badge_y, x_left + badge_size, badge_y + badge_size],
                    radius=3,
                    outline=badge_color,
                    width=1,
                )

            # 居中写排名数字
            num_str = str(index)
            num_font = load_font("inter_bold", max(9, int(badge_size * 0.72)))
            nbb = ctx.draw.textbbox((0, 0), num_str, font=num_font)
            nw = nbb[2] - nbb[0]
            nh = nbb[3] - nbb[1]
            ctx.draw.text(
                (x_left + (badge_size - nw) // 2, badge_y + (badge_size - nh) // 2 - 1),
                num_str,
                fill=badge_text_color,
                font=num_font,
            )

            # 2. 右侧元数据胶囊（如评分、热度、标签）
            tag = str(item.get("rating_label") or item.get("views_label") or item.get("category") or "").strip()
            if not tag and subtitle and len(subtitle) <= 6:
                tag = subtitle

            tag_w = 0
            if tag and ctx.available_width >= 240:
                tag_font = load_font("noto_serif_regular", max(8, int(font_size * 0.82)))
                tbb = ctx.draw.textbbox((0, 0), tag, font=tag_font)
                tw = tbb[2] - tbb[0]
                th = tbb[3] - tbb[1]
                pill_w = tw + int(8 * ctx.scale)
                pill_h = max(th + int(2 * ctx.scale), int(badge_size * 0.9))
                pill_x = ctx.x_offset + ctx.available_width - pill_w - int(8 * ctx.scale)
                pill_y = y + (row_h - pill_h) // 2
                ctx.draw.rounded_rectangle(
                    [pill_x, pill_y, pill_x + pill_w, pill_y + pill_h],
                    radius=3,
                    outline=EINK_FG,
                    width=1,
                )
                ctx.draw.text(
                    (pill_x + int(4 * ctx.scale), pill_y + (pill_h - th) // 2 - 1),
                    tag,
                    fill=EINK_FG,
                    font=tag_font,
                )
                tag_w = pill_w + int(8 * ctx.scale)

            # 3. 主标题与副标题排版
            text_x = x_left + badge_size + int(8 * ctx.scale)
            max_text_w = max(60, ctx.available_width - (text_x - ctx.x_offset) - tag_w - int(6 * ctx.scale))
            
            main_title = title
            t_bb = ctx.draw.textbbox((0, 0), main_title, font=bold)
            while (t_bb[2] - t_bb[0]) > max_text_w and len(main_title) > 2:
                main_title = main_title[:-1]
                t_bb = ctx.draw.textbbox((0, 0), main_title + "...", font=bold)
            if len(main_title) < len(title):
                main_title += "..."

            text_y = y + (row_h - font_size) // 2
            ctx.draw.text((text_x, text_y), main_title, fill=EINK_FG, font=bold)
            title_rendered_w = ctx.draw.textbbox((0, 0), main_title, font=bold)[2] - t_bb[0]

            # 若还有可用空间且有未作为 tag 的 subtitle，在主标题后以浅色字紧随
            if subtitle and subtitle != tag and (max_text_w - title_rendered_w) > int(45 * ctx.scale):
                sub_font = load_font("noto_serif_light", max(9, int(font_size * 0.88)))
                sub_text = f" · {subtitle}"
                sub_bb = ctx.draw.textbbox((0, 0), sub_text, font=sub_font)
                avail_sub_w = max_text_w - title_rendered_w - int(4 * ctx.scale)
                while (sub_bb[2] - sub_bb[0]) > avail_sub_w and len(sub_text) > 4:
                    sub_text = sub_text[:-1]
                    sub_bb = ctx.draw.textbbox((0, 0), sub_text + "...", font=sub_font)
                if len(sub_text) < len(f" · {subtitle}"):
                    sub_text += "..."
                ctx.draw.text((text_x + title_rendered_w + int(4 * ctx.scale), text_y + 1), sub_text, fill=EINK_FG, font=sub_font)

            # 4. 行间微细虚线分隔
            if index < len(items_to_render):
                sep_y = y + row_h - 1
                draw_dashed_line(
                    ctx.draw,
                    (x_left, sep_y),
                    (ctx.x_offset + ctx.available_width - int(8 * ctx.scale), sep_y),
                    fill=EINK_FG,
                    width=1,
                    dash_len=2,
                    gap_len=3,
                )

            y += row_h
    ctx.y = y
