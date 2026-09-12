"""Compact recommendation list/card renderer for external media modes."""
from __future__ import annotations
from PIL import ImageDraw
from .context import RenderContext
from .registry import register_block
from .text import pick_cjk_font
from .components import render_image
from ..patterns.utils import load_font, EINK_FG


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

                if image_data is not None or image_url:
                    previous_image = ctx.content.get("__recommendation_image")
                    ctx.content["__recommendation_image"] = image_data if image_data is not None else image_url
                    render_image(ctx, {
                        "field": "__recommendation_image",
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
            line = f"{rank}  {title}"
            if subtitle: line += f" · {subtitle}"
            max_chars = max(10, int((ctx.available_width - int(20 * ctx.scale)) / (font_size * 0.72)))
            ctx.draw.text((ctx.x_offset + int(10 * ctx.scale), y), line[:max_chars], fill=EINK_FG, font=font)
            y += font_size + int(3 * ctx.scale)
    ctx.y = y
