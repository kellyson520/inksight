"""
InkSight 扩充排版组件库 9：边框、徽章与排版饰件组件 (Frames, Badges & Ornaments)
包含：
121. dashed_frame_box: 细密虚线外包框
122. double_line_capsule: 双细线椭圆胶囊
123. dotted_separator_line: 点状分割虚线
124. star_rating_row: 星星评级打分条
125. version_tag_stamp: 软件版本号印章
126. ribbon_bookmark_corner: 右上角折叠书签角标
127. vintage_flourish_divider: 维多利亚对称卷花分隔线
128. diamond_bullet_list: 菱形项目符号列表项
129. bracket_annotation_pair: 左右粗方括号标注对
130. hatched_texture_banner: 斜线阴影纹理饰带
131. pill_badge_inverted: 反色实心小徽标
132. corner_triangle_flag: 三角旗直角徽标
133. serrated_edge_strip: 邮票齿孔连续边缘
134. heraldic_crest_shield: 纹章盾牌轮廓框
135. chevron_arrow_pointer: 箭头双角形导航指示
136. dotted_circle_badge: 虚线圆圈环绕数字
137. square_bracket_tag: 方括号技术标号
138. wavy_underline_accent: 波浪波纹强调下划线
139. pill_counter_bubble: 圆形气泡角标计数器
140. ornate_end_flourish: 篇末收尾对称印记
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


@register_block("dashed_frame_box")
def render_dashed_frame_box(ctx: RenderContext, block: dict) -> None:
    """细密虚线外包框。"""
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 6) * ctx.scale)
    x = ctx.x_offset + margin_x
    y = ctx.y
    w = ctx.available_width - margin_x * 2
    h = 24

    for dx in range(0, w, 4):
        ctx.draw.line((x + dx, y, x + dx + 2, y), fill=EINK_FG, width=1)
        ctx.draw.line((x + dx, y + h, x + dx + 2, y + h), fill=EINK_FG, width=1)
    for dy in range(0, h, 4):
        ctx.draw.line((x, y + dy, x, y + dy + 2), fill=EINK_FG, width=1)
        ctx.draw.line((x + w, y + dy, x + w, y + dy + 2), fill=EINK_FG, width=1)
    font = load_font("noto_serif_regular", int(8 * ctx.scale))
    ctx.draw.text((x + 8, y + 6), "DASHED BOUNDARY CONTAINER", fill=EINK_FG, font=font)
    ctx.y = y + h + margin_bottom


@register_block("double_line_capsule")
def render_double_line_capsule(ctx: RenderContext, block: dict) -> None:
    """双细线椭圆胶囊。"""
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 4) * ctx.scale)
    text = str(block.get("text", "RELEASE v2.5"))
    x = ctx.x_offset + margin_x
    y = ctx.y

    font = load_font("noto_serif_bold", int(8 * ctx.scale))
    tb = safe_font_bbox(font, text)
    bw = (tb[2] - tb[0]) + 16
    _draw_box(ctx.draw, (x, y, x + bw, y + 14), outline=EINK_FG, width=1)
    _draw_box(ctx.draw, (x + 2, y + 2, x + bw - 2, y + 12), outline=EINK_FG, width=1)
    ctx.draw.text((x + 8, y + 2), text, fill=EINK_FG, font=font)
    ctx.y = y + 16 + margin_bottom


@register_block("dotted_separator_line")
def render_dotted_separator_line(ctx: RenderContext, block: dict) -> None:
    """点状分割线。"""
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 4) * ctx.scale)
    x = ctx.x_offset + margin_x
    y = ctx.y
    w = ctx.available_width - margin_x * 2

    for dx in range(0, w, 5):
        ctx.draw.ellipse((x + dx, y, x + dx + 1, y + 1), fill=EINK_FG)
    ctx.y = y + 4 + margin_bottom


@register_block("star_rating_row")
def render_star_rating_row(ctx: RenderContext, block: dict) -> None:
    """星级评级打分条 (5星)。"""
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 4) * ctx.scale)
    stars = int(block.get("stars", 4))
    x = ctx.x_offset + margin_x
    y = ctx.y

    font = load_font("noto_serif_regular", int(8 * ctx.scale))
    ctx.draw.text((x, y), "RATING:", fill=EINK_FG, font=font)
    sx = x + 50
    for i in range(5):
        bx = sx + i * 10
        fill = EINK_FG if i < stars else None
        # 菱形模拟星
        ctx.draw.polygon([(bx + 3, y), (bx + 6, y + 4), (bx + 3, y + 8), (bx, y + 4)], outline=EINK_FG, fill=fill)
    ctx.y = y + 11 + margin_bottom


@register_block("version_tag_stamp")
def render_version_tag_stamp(ctx: RenderContext, block: dict) -> None:
    """软件版本印章。"""
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 4) * ctx.scale)
    ver = str(block.get("ver", "BUILD #1042"))
    x = ctx.x_offset + margin_x
    y = ctx.y

    font = load_font("noto_serif_bold", int(8 * ctx.scale))
    tb = safe_font_bbox(font, ver)
    bw = (tb[2] - tb[0]) + 10
    _draw_box(ctx.draw, (x, y, x + bw, y + 12), outline=EINK_FG, width=1)
    ctx.draw.text((x + 5, y + 1), ver, fill=EINK_FG, font=font)
    ctx.y = y + 14 + margin_bottom


@register_block("ribbon_bookmark_corner")
def render_ribbon_bookmark_corner(ctx: RenderContext, block: dict) -> None:
    """角标书签。"""
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 4) * ctx.scale)
    tag = str(block.get("tag", "PRO"))
    x = ctx.x_offset + margin_x
    y = ctx.y

    _draw_box(ctx.draw, (x, y, x + 24, y + 12), fill=EINK_FG)
    ctx.draw.polygon([(x, y + 12), (x + 12, y + 8), (x + 24, y + 12)], fill=EINK_BG)
    font = load_font("noto_serif_bold", int(7 * ctx.scale))
    ctx.draw.text((x + 4, y + 1), tag, fill=EINK_BG, font=font)
    ctx.y = y + 14 + margin_bottom


@register_block("vintage_flourish_divider")
def render_vintage_flourish_divider(ctx: RenderContext, block: dict) -> None:
    """对称卷花分隔线。"""
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 4) * ctx.scale)
    x = ctx.x_offset + margin_x
    y = ctx.y
    w = ctx.available_width - margin_x * 2
    cx = x + w // 2

    ctx.draw.line((x, y + 3, cx - 12, y + 3), fill=EINK_FG, width=1)
    ctx.draw.line((cx + 12, y + 3, x + w, y + 3), fill=EINK_FG, width=1)
    ctx.draw.ellipse((cx - 4, y, cx + 4, y + 6), outline=EINK_FG, fill=EINK_FG)
    ctx.y = y + 8 + margin_bottom


@register_block("diamond_bullet_list")
def render_diamond_bullet_list(ctx: RenderContext, block: dict) -> None:
    """菱形项目符号列表项。"""
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 3) * ctx.scale)
    item = str(block.get("item", "High-performance modular architecture"))
    x = ctx.x_offset + margin_x
    y = ctx.y

    ctx.draw.polygon([(x + 3, y + 2), (x + 6, y + 5), (x + 3, y + 8), (x, y + 5)], fill=EINK_FG)
    font = load_font("noto_serif_regular", int(8 * ctx.scale))
    ctx.draw.text((x + 12, y), item, fill=EINK_FG, font=font)
    ctx.y = y + 11 + margin_bottom


@register_block("bracket_annotation_pair")
def render_bracket_annotation_pair(ctx: RenderContext, block: dict) -> None:
    """左右粗方括号标注对。"""
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 4) * ctx.scale)
    text = str(block.get("text", "CORE ARCHITECTURE"))
    x = ctx.x_offset + margin_x
    y = ctx.y

    font = load_font("noto_serif_bold", int(9 * ctx.scale))
    ctx.draw.text((x, y), f"[[ {text} ]]", fill=EINK_FG, font=font)
    ctx.y = y + 13 + margin_bottom


@register_block("hatched_texture_banner")
def render_hatched_texture_banner(ctx: RenderContext, block: dict) -> None:
    """斜线阴影饰带。"""
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 4) * ctx.scale)
    x = ctx.x_offset + margin_x
    y = ctx.y
    w = ctx.available_width - margin_x * 2
    h = 8

    _draw_box(ctx.draw, (x, y, x + w, y + h), outline=EINK_FG, width=1)
    for dx in range(0, w, 4):
        ctx.draw.line((x + dx, y, x + dx + 3, y + h), fill=EINK_FG, width=1)
    ctx.y = y + h + margin_bottom


@register_block("pill_badge_inverted")
def render_pill_badge_inverted(ctx: RenderContext, block: dict) -> None:
    """反色实心小徽标。"""
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 4) * ctx.scale)
    badge = str(block.get("badge", "STABLE"))
    x = ctx.x_offset + margin_x
    y = ctx.y

    font = load_font("noto_serif_bold", int(8 * ctx.scale))
    tb = safe_font_bbox(font, badge)
    bw = (tb[2] - tb[0]) + 10
    _draw_box(ctx.draw, (x, y, x + bw, y + 12), fill=EINK_FG)
    ctx.draw.text((x + 5, y + 1), badge, fill=EINK_BG, font=font)
    ctx.y = y + 14 + margin_bottom


@register_block("corner_triangle_flag")
def render_corner_triangle_flag(ctx: RenderContext, block: dict) -> None:
    """直角三角旗徽标。"""
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 4) * ctx.scale)
    x = ctx.x_offset + margin_x
    y = ctx.y

    ctx.draw.polygon([(x, y), (x + 14, y), (x, y + 14)], fill=EINK_FG)
    ctx.y = y + 16 + margin_bottom


@register_block("serrated_edge_strip")
def render_serrated_edge_strip(ctx: RenderContext, block: dict) -> None:
    """邮票齿孔连续边缘。"""
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 4) * ctx.scale)
    x = ctx.x_offset + margin_x
    y = ctx.y
    w = ctx.available_width - margin_x * 2

    for dx in range(0, w, 6):
        ctx.draw.polygon([(x + dx, y), (x + dx + 3, y + 4), (x + dx + 6, y)], fill=EINK_FG)
    ctx.y = y + 6 + margin_bottom


@register_block("heraldic_crest_shield")
def render_heraldic_crest_shield(ctx: RenderContext, block: dict) -> None:
    """纹章盾牌轮廓框。"""
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 4) * ctx.scale)
    x = ctx.x_offset + margin_x
    y = ctx.y

    pts = [(x, y), (x + 16, y), (x + 16, y + 10), (x + 8, y + 16), (x, y + 10)]
    ctx.draw.polygon(pts, outline=EINK_FG, fill=None)
    ctx.y = y + 18 + margin_bottom


@register_block("chevron_arrow_pointer")
def render_chevron_arrow_pointer(ctx: RenderContext, block: dict) -> None:
    """箭头双角形导航指示。"""
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 4) * ctx.scale)
    x = ctx.x_offset + margin_x
    y = ctx.y

    ctx.draw.line((x, y, x + 5, y + 5), fill=EINK_FG, width=2)
    ctx.draw.line((x + 5, y + 5, x, y + 10), fill=EINK_FG, width=2)
    ctx.y = y + 12 + margin_bottom


@register_block("dotted_circle_badge")
def render_dotted_circle_badge(ctx: RenderContext, block: dict) -> None:
    """虚线圆圈环绕数字。"""
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 4) * ctx.scale)
    num = str(block.get("num", "1"))
    x = ctx.x_offset + margin_x
    y = ctx.y

    for deg in range(0, 360, 45):
        rad = deg * 3.14159 / 180.0
        cx = x + 7 + int(6 * 1.0 * (1 if deg % 90 == 0 else 0.7))
        cy = y + 7 + int(6 * 1.0 * (0 if deg % 90 == 0 else 0.7))
        ctx.draw.point((cx, cy), fill=EINK_FG)
    font = load_font("noto_serif_bold", int(8 * ctx.scale))
    ctx.draw.text((x + 4, y + 2), num, fill=EINK_FG, font=font)
    ctx.y = y + 16 + margin_bottom


@register_block("square_bracket_tag")
def render_square_bracket_tag(ctx: RenderContext, block: dict) -> None:
    """方括号技术标号。"""
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 3) * ctx.scale)
    tag = str(block.get("tag", "RFC-9110"))
    x = ctx.x_offset + margin_x
    y = ctx.y

    font = load_font("noto_serif_regular", int(8 * ctx.scale))
    ctx.draw.text((x, y), f"[{tag}]", fill=EINK_FG, font=font)
    ctx.y = y + 11 + margin_bottom


@register_block("wavy_underline_accent")
def render_wavy_underline_accent(ctx: RenderContext, block: dict) -> None:
    """波浪波纹强调线。"""
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 4) * ctx.scale)
    x = ctx.x_offset + margin_x
    y = ctx.y
    w = ctx.available_width - margin_x * 2

    for dx in range(0, w, 6):
        ctx.draw.arc((x + dx, y, x + dx + 3, y + 4), start=0, end=180, fill=EINK_FG)
        ctx.draw.arc((x + dx + 3, y, x + dx + 6, y + 4), start=180, end=360, fill=EINK_FG)
    ctx.y = y + 6 + margin_bottom


@register_block("pill_counter_bubble")
def render_pill_counter_bubble(ctx: RenderContext, block: dict) -> None:
    """圆形气泡角标计数。"""
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 4) * ctx.scale)
    cnt = str(block.get("cnt", "99+"))
    x = ctx.x_offset + margin_x
    y = ctx.y

    font = load_font("noto_serif_bold", int(7 * ctx.scale))
    tb = safe_font_bbox(font, cnt)
    bw = (tb[2] - tb[0]) + 8
    _draw_box(ctx.draw, (x, y, x + bw, y + 10), fill=EINK_FG)
    ctx.draw.text((x + 4, y), cnt, fill=EINK_BG, font=font)
    ctx.y = y + 12 + margin_bottom


@register_block("ornate_end_flourish")
def render_ornate_end_flourish(ctx: RenderContext, block: dict) -> None:
    """篇末收尾对称印记。"""
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 6) * ctx.scale)
    x = ctx.x_offset + margin_x
    y = ctx.y
    w = ctx.available_width - margin_x * 2
    cx = x + w // 2

    ctx.draw.line((cx - 20, y + 2, cx - 4, y + 2), fill=EINK_FG, width=1)
    ctx.draw.line((cx + 4, y + 2, cx + 20, y + 2), fill=EINK_FG, width=1)
    ctx.draw.ellipse((cx - 2, y, cx + 2, y + 4), fill=EINK_FG)
    ctx.y = y + 6 + margin_bottom
