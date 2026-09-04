"""
自然灾害图标与紧急避险预警组件模块 (Natural Disaster Icons & Emergency Alert Blocks)
包含 12 大类矢量墨水屏灾害图标与预警卡片：
1. 台风/飓风 (typhoon)
2. 暴雨/洪涝 (rainstorm)
3. 暴雪/道路结冰 (blizzard)
4. 大风/强对流 (gale)
5. 高温/酷热 (extreme_heat)
6. 寒潮/严寒 (cold_wave)
7. 地震 (earthquake)
8. 森林火险/野火 (wildfire)
9. 海啸 (tsunami)
10. 冰雹 (hail)
11. 沙尘暴 (sandstorm)
12. 大雾/雾霾 (fog)
"""
from __future__ import annotations

import logging
import math
from typing import Any

from PIL import Image, ImageDraw

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

_DEFAULT_RED = EINK_COLOR_NAME_MAP.get("red", 2)


def _draw_rounded_rect(draw, bbox, radius, fill=None, outline=None, width=1):
    try:
        draw.rounded_rectangle(bbox, radius=radius, fill=fill, outline=outline, width=width)
    except AttributeError:
        draw.rectangle(bbox, fill=fill, outline=outline, width=width)


def draw_disaster_vector_icon(
    draw: ImageDraw.ImageDraw,
    hazard: str,
    cx: int,
    cy: int,
    size: int = 40,
    color: int = EINK_FG,
    accent_color: int = _DEFAULT_RED,
) -> None:
    """在 (cx, cy) 为中心绘制指定灾害类型的矢量墨水屏高对比度图标。"""
    r = size // 2
    h_type = (hazard or "typhoon").lower()

    if "typhoon" in h_type or "hurricane" in h_type or "台风" in h_type or "飓风" in h_type:
        # 台风双螺旋风眼
        draw.arc([(cx - r, cy - r), (cx + r, cy + r)], start=30, end=170, fill=color, width=3)
        draw.arc([(cx - r, cy - r), (cx + r, cy + r)], start=210, end=350, fill=color, width=3)
        draw.arc([(cx - r // 2, cy - r // 2), (cx + r // 2, cy + r // 2)], start=120, end=270, fill=color, width=2)
        draw.ellipse([(cx - 3, cy - 3), (cx + 3, cy + 3)], fill=accent_color)

    elif "rain" in h_type or "flood" in h_type or "暴雨" in h_type or "雨" in h_type or "水" in h_type:
        # 乌云 + 倾斜暴雨线
        cloud_y = cy - r // 4
        draw.ellipse([(cx - r + 4, cloud_y - 6), (cx - 2, cloud_y + 8)], fill=color)
        draw.ellipse([(cx - 6, cloud_y - 12), (cx + 10, cloud_y + 8)], fill=color)
        draw.ellipse([(cx + 2, cloud_y - 8), (cx + r - 2, cloud_y + 8)], fill=color)
        # 倾斜雨滴
        for off_x in (-r // 2, 0, r // 2):
            draw.line([(cx + off_x - 2, cloud_y + 12), (cx + off_x - 6, cloud_y + 20)], fill=accent_color, width=2)

    elif "snow" in h_type or "blizzard" in h_type or "暴雪" in h_type or "雪" in h_type:
        # 六角雪花晶体
        for angle in (0, 60, 120):
            rad = math.radians(angle)
            dx = int(math.cos(rad) * (r - 2))
            dy = int(math.sin(rad) * (r - 2))
            draw.line([(cx - dx, cy - dy), (cx + dx, cy + dy)], fill=color, width=2)
            # 枝杈
            for s in (-1, 1):
                bx = cx + dx * s * 2 // 3
                by = cy + dy * s * 2 // 3
                draw.line([(bx, by), (bx + int(dx * 0.3), by - int(dy * 0.3))], fill=color, width=1)
        draw.ellipse([(cx - 3, cy - 3), (cx + 3, cy + 3)], fill=accent_color)

    elif "wind" in h_type or "gale" in h_type or "大风" in h_type or "强对流" in h_type:
        # 疾风气流线与箭头
        for i, dy in enumerate((-r // 3, 0, r // 3)):
            w = r - abs(dy)
            draw.line([(cx - w, cy + dy), (cx + w, cy + dy)], fill=color if i != 1 else accent_color, width=2)
            draw.line([(cx + w, cy + dy), (cx + w - 4, cy + dy - 3)], fill=color if i != 1 else accent_color, width=2)

    elif "heat" in h_type or "高温" in h_type or "酷热" in h_type:
        # 烈日放射光芒 + 高温计
        draw.ellipse([(cx - r // 2, cy - r // 2), (cx + r // 2, cy + r // 2)], outline=accent_color, width=2)
        for ang in range(0, 360, 45):
            rad = math.radians(ang)
            x1 = cx + int(math.cos(rad) * (r // 2 + 2))
            y1 = cy + int(math.sin(rad) * (r // 2 + 2))
            x2 = cx + int(math.cos(rad) * (r - 1))
            y2 = cy + int(math.sin(rad) * (r - 1))
            draw.line([(x1, y1), (x2, y2)], fill=accent_color, width=2)
        # 中心警示圆
        draw.ellipse([(cx - 4, cy - 4), (cx + 4, cy + 4)], fill=color)

    elif "cold" in h_type or "freeze" in h_type or "寒潮" in h_type or "低温" in h_type:
        # 低温计 + 冰柱
        tx = cx
        draw.line([(tx, cy - r + 4), (tx, cy + r // 2)], fill=color, width=4)
        draw.ellipse([(tx - 6, cy + r // 2 - 2), (tx + 6, cy + r - 2)], fill=color)
        draw.ellipse([(tx - 3, cy + r // 2 + 1), (tx + 3, cy + r - 5)], fill=accent_color)
        # 侧边刻度
        for dy in (-r // 2, -r // 4, 0):
            draw.line([(tx + 4, cy + dy), (tx + 9, cy + dy)], fill=color, width=1)

    elif "earthquake" in h_type or "地震" in h_type:
        # 大地断裂锯齿波
        y_ground = cy - r // 4
        draw.line([(cx - r, y_ground), (cx + r, y_ground)], fill=color, width=2)
        # 地震震波折线
        points = [
            (cx - r + 2, cy + r // 3),
            (cx - r // 2, cy + r // 3),
            (cx - r // 4, cy - r // 3),
            (cx, cy + r // 2),
            (cx + r // 4, cy - r // 2),
            (cx + r // 2, cy + r // 4),
            (cx + r - 2, cy + r // 4),
        ]
        draw.line(points, fill=accent_color, width=2)

    elif "fire" in h_type or "wildfire" in h_type or "火" in h_type:
        # 烈火火苗
        draw.polygon([
            (cx, cy - r + 2),
            (cx + r // 2, cy),
            (cx + r // 3, cy + r - 3),
            (cx - r // 3, cy + r - 3),
            (cx - r // 2, cy),
        ], fill=accent_color)
        # 内火苗
        draw.polygon([
            (cx, cy - r // 4),
            (cx + r // 4, cy + r // 3),
            (cx - r // 4, cy + r // 3),
        ], fill=color)

    elif "tsunami" in h_type or "海啸" in h_type:
        # 翻卷的海啸巨浪
        draw.arc([(cx - r, cy - r // 2), (cx + r // 2, cy + r)], start=180, end=350, fill=color, width=3)
        draw.arc([(cx - r // 3, cy - r + 2), (cx + r - 2, cy + r // 2)], start=150, end=300, fill=accent_color, width=3)
        draw.line([(cx - r, cy + r - 4), (cx + r, cy + r - 4)], fill=color, width=2)

    elif "hail" in h_type or "冰雹" in h_type:
        # 云朵 + 坚硬六角/方块下落
        cloud_y = cy - r // 3
        draw.ellipse([(cx - r + 4, cloud_y - 4), (cx + r - 4, cloud_y + 8)], fill=color)
        # 冰雹块
        for off_x, off_y in [(-r // 3, r // 4), (0, r // 2), (r // 3, r // 4)]:
            bx, by = cx + off_x, cy + off_y
            draw.rectangle([(bx - 3, by - 3), (bx + 3, by + 3)], fill=accent_color)

    elif "sand" in h_type or "sandstorm" in h_type or "沙尘" in h_type:
        # 沙尘暴横扫颗粒风暴
        for i in range(5):
            ly = cy - r + i * (size // 4)
            draw.line([(cx - r + i * 4, ly), (cx + r - i * 2, ly)], fill=color, width=1)
        for px, py in [(-8, -4), (6, 2), (-3, 8), (10, -6), (2, -10)]:
            draw.rectangle([(cx + px, cy + py), (cx + px + 2, cy + py + 2)], fill=accent_color)

    else:  # "fog" or default
        # 大雾/霾：三道层叠迷雾
        for dy in (-r // 2, 0, r // 2):
            draw.line([(cx - r + 4, cy + dy), (cx + r - 4, cy + dy)], fill=color, width=3)
        draw.line([(cx - r // 2, cy + r // 4), (cx + r // 2, cy + r // 4)], fill=accent_color, width=2)


@register_block("disaster_icon")
def render_disaster_icon(ctx: RenderContext, block: dict) -> None:
    """独立灾害图标组件。"""
    hazard = str(block.get("hazard") or ctx.resolve(block.get("hazard_template") or "") or "typhoon")
    size = int(block.get("size", 44) * ctx.scale)
    align = block.get("align", "center")
    margin_x = int(block.get("margin_x", 12) * ctx.scale)

    if align == "left":
        cx = ctx.x_offset + margin_x + size // 2
    elif align == "right":
        cx = ctx.x_offset + ctx.available_width - margin_x - size // 2
    else:
        cx = ctx.x_offset + ctx.available_width // 2

    cy = ctx.y + size // 2
    fg_col = ctx.resolve_color({"color": block.get("color", "black")})
    acc_col = ctx.resolve_color({"color": block.get("accent_color", "red")})

    draw_disaster_vector_icon(ctx.draw, hazard, cx, cy, size=size, color=fg_col, accent_color=acc_col)
    ctx.y += size + int(block.get("margin_bottom", 6) * ctx.scale)


@register_block("disaster_banner")
def render_disaster_banner(ctx: RenderContext, block: dict) -> None:
    """最高优先级紧急灾害横幅（醒目高反差大字框 + 预警级别红底标）。"""
    level = str(block.get("level") or ctx.resolve(block.get("level_template") or "") or "黄色")
    hazard = str(block.get("hazard") or ctx.resolve(block.get("hazard_template") or "") or "气象灾害")
    sender = str(block.get("sender") or ctx.resolve(block.get("sender_template") or "") or "国家气象局")
    pub_time = str(block.get("time") or ctx.resolve(block.get("time_template") or "") or "")

    margin_x = int(block.get("margin_x", 8) * ctx.scale)
    x0 = ctx.x_offset + margin_x
    x1 = ctx.x_offset + ctx.available_width - margin_x
    y0 = ctx.y
    banner_h = int(block.get("height", 46) * ctx.scale)
    y1 = y0 + banner_h

    # 外框：黑粗外框
    _draw_rounded_rect(ctx.draw, [(x0, y0), (x1, y1)], radius=int(4 * ctx.scale), outline=EINK_FG, width=int(2 * ctx.scale))

    # 预警级别色块（红色预警用纯红，其他用纯黑）
    level_is_red = "红" in level or "RED" in level.upper()
    badge_bg = ctx.color_index("red") if (level_is_red and ctx.colors >= 3) else EINK_FG
    badge_w = int(58 * ctx.scale)
    _draw_rounded_rect(ctx.draw, [(x0, y0), (x0 + badge_w, y1)], radius=int(4 * ctx.scale), fill=badge_bg)

    # 级别文字
    lvl_font = load_font("noto_serif_bold", int(14 * ctx.scale))
    lb = safe_font_bbox(lvl_font, level)
    lw, lh = lb[2] - lb[0], lb[3] - lb[1]
    ctx.draw.text((x0 + (badge_w - lw) // 2, y0 + (banner_h - lh) // 2 - 2), level, fill=EINK_BG, font=lvl_font)

    # 标题正文
    title_text = f"【{hazard}预警】"
    t_font = load_font("noto_serif_bold", int(16 * ctx.scale))
    ctx.draw.text((x0 + badge_w + int(8 * ctx.scale), y0 + int(6 * ctx.scale)), title_text, fill=EINK_FG, font=t_font)

    # 发送方与时间
    sub_text = f"{sender} · {pub_time}" if pub_time else sender
    s_font = load_font("inter_medium", max(9, int(10 * ctx.scale)))
    ctx.draw.text((x0 + badge_w + int(10 * ctx.scale), y0 + int(26 * ctx.scale)), sub_text, fill=EINK_FG, font=s_font)

    ctx.y = y1 + int(block.get("margin_bottom", 8) * ctx.scale)


@register_block("disaster_advice_box")
def render_disaster_advice_box(ctx: RenderContext, block: dict) -> None:
    """灾害应急防范指南容器（带警告立柱与防范要点清单）。"""
    title = str(block.get("title") or "防御指南与避险提示")
    advice_items = block.get("items") or ctx.get_field("advice") or []
    if isinstance(advice_items, str):
        advice_items = [advice_items]

    margin_x = int(block.get("margin_x", 10) * ctx.scale)
    x0 = ctx.x_offset + margin_x
    x1 = ctx.x_offset + ctx.available_width - margin_x
    y_start = ctx.y

    # 左侧红色预警警示立柱
    bar_w = int(4 * ctx.scale)
    bar_color = ctx.color_index("red") if ctx.colors >= 3 else EINK_FG

    title_font = load_font("noto_serif_bold", int(12 * ctx.scale))
    ctx.draw.text((x0 + bar_w + int(8 * ctx.scale), y_start), title, fill=EINK_FG, font=title_font)
    cur_y = y_start + int(18 * ctx.scale)

    item_font = load_font("noto_serif_regular", int(11 * ctx.scale))
    line_h = int(16 * ctx.scale)
    max_text_w = x1 - (x0 + bar_w + int(10 * ctx.scale))

    for idx, item in enumerate(advice_items[:4]):
        text = f"{idx + 1}. {item}" if len(advice_items) > 1 else str(item)
        lines = wrap_text(text, item_font, max_text_w)
        for ln in lines:
            if cur_y + line_h > ctx.footer_top - 4:
                break
            ctx.draw.text((x0 + bar_w + int(10 * ctx.scale), cur_y), ln, fill=EINK_FG, font=item_font)
            cur_y += line_h

    # 绘制立柱全高
    ctx.draw.rectangle([(x0, y_start), (x0 + bar_w, cur_y)], fill=bar_color)
    ctx.y = cur_y + int(block.get("margin_bottom", 8) * ctx.scale)


@register_block("disaster_level_meter")
def render_disaster_level_meter(ctx: RenderContext, block: dict) -> None:
    """国家标准四级预警刻度指示条：[ 蓝 IV | 黄 III | 橙 II | 红 I ]。

    指示条横向等分排列四级，高亮当前激活级别并附带指示三角。
    """
    raw_level = str(block.get("level") or ctx.resolve(block.get("level_template") or "") or "黄色").strip().lower()

    # 确定激活索引 0:蓝, 1:黄, 2:橙, 3:红
    if "红" in raw_level or "red" in raw_level or "i级" in raw_level:
        active_idx = 3
    elif "橙" in raw_level or "orange" in raw_level or "ii级" in raw_level:
        active_idx = 2
    elif "黄" in raw_level or "yellow" in raw_level or "iii级" in raw_level:
        active_idx = 1
    elif "蓝" in raw_level or "blue" in raw_level or "iv级" in raw_level:
        active_idx = 0
    else:
        active_idx = 1

    margin_x = int(block.get("margin_x", 12) * ctx.scale)
    avail_w = ctx.available_width - margin_x * 2
    x_start = ctx.x_offset + margin_x
    y_start = ctx.y
    meter_h = int(block.get("height", 24) * ctx.scale)
    y_end = y_start + meter_h

    # 四级定义：标签 + 级别
    segments = [
        ("蓝 IV", "一般"),
        ("黄 III", "较重"),
        ("橙 II", "严重"),
        ("红 I", "特重"),
    ]
    seg_w = avail_w // 4
    seg_font = load_font("noto_serif_bold", int(11 * ctx.scale))

    for idx, (title, sub) in enumerate(segments):
        sx0 = x_start + idx * seg_w
        sx1 = sx0 + seg_w - int(2 * ctx.scale)
        is_active = (idx == active_idx)

        if is_active:
            # 激活状态：红色/橙色使用红底反白，黄色/蓝色使用黑底反白
            if idx >= 2 and ctx.colors >= 3:
                bg = ctx.color_index("red")
            else:
                bg = EINK_FG
            _draw_rounded_rect(ctx.draw, [(sx0, y_start), (sx1, y_end)], radius=int(3 * ctx.scale), fill=bg)
            text_col = EINK_BG
        else:
            # 未激活：细线边框 + 背景留白
            _draw_rounded_rect(ctx.draw, [(sx0, y_start), (sx1, y_end)], radius=int(3 * ctx.scale), outline=EINK_FG, width=1)
            text_col = EINK_FG

        # 绘制文本居中
        tb = safe_font_bbox(seg_font, title)
        tw, th = tb[2] - tb[0], tb[3] - tb[1]
        ctx.draw.text((sx0 + (seg_w - tw) // 2, y_start + (meter_h - th) // 2 - 1), title, fill=text_col, font=seg_font)

        # 在激活项上方或下方绘制小三角形指示标 ▲
        if is_active:
            tri_cx = sx0 + seg_w // 2 - 1
            tri_y = y_end + int(2 * ctx.scale)
            tri_sz = int(3 * ctx.scale)
            ctx.draw.polygon([
                (tri_cx, tri_y),
                (tri_cx - tri_sz, tri_y + tri_sz * 2),
                (tri_cx + tri_sz, tri_y + tri_sz * 2),
            ], fill=ctx.color_index("red") if (idx >= 2 and ctx.colors >= 3) else EINK_FG)

    ctx.y = y_end + int(block.get("margin_bottom", 10) * ctx.scale)


@register_block("disaster_level_badge")
def render_disaster_level_badge(ctx: RenderContext, block: dict) -> None:
    """独立预警级别徽章，支持同时输出预警颜色、罗马数字及严重度。"""
    raw_level = str(block.get("level") or ctx.resolve(block.get("level_template") or "") or "黄色")
    align = block.get("align", "left")

    if "红" in raw_level:
        badge_text = "红色预警 · I级 特别严重"
        is_red = True
    elif "橙" in raw_level:
        badge_text = "橙色预警 · II级 严重"
        is_red = True
    elif "黄" in raw_level:
        badge_text = "黄色预警 · III级 较重"
        is_red = False
    elif "蓝" in raw_level:
        badge_text = "蓝色预警 · IV级 一般"
        is_red = False
    else:
        badge_text = f"{raw_level}预警"
        is_red = False

    font = load_font("noto_serif_bold", int(11 * ctx.scale))
    bb = safe_font_bbox(font, badge_text)
    bw, bh = bb[2] - bb[0], bb[3] - bb[1]

    pad_x = int(8 * ctx.scale)
    pad_y = int(3 * ctx.scale)
    total_w = bw + pad_x * 2
    total_h = bh + pad_y * 2

    margin_x = int(block.get("margin_x", 12) * ctx.scale)
    if align == "center":
        x0 = ctx.x_offset + (ctx.available_width - total_w) // 2
    elif align == "right":
        x0 = ctx.x_offset + ctx.available_width - margin_x - total_w
    else:
        x0 = ctx.x_offset + margin_x
    y0 = ctx.y

    bg_color = ctx.color_index("red") if (is_red and ctx.colors >= 3) else EINK_FG
    _draw_rounded_rect(ctx.draw, [(x0, y0), (x0 + total_w, y0 + total_h)], radius=int(3 * ctx.scale), fill=bg_color)
    ctx.draw.text((x0 + pad_x, y0 + pad_y - 1), badge_text, fill=EINK_BG, font=font)

    ctx.y = y0 + total_h + int(block.get("margin_bottom", 6) * ctx.scale)


@register_block("disaster_hero")
def render_disaster_hero(ctx: RenderContext, block: dict) -> None:
    """灾害核心区域：
    1. 顶部：当前预警级别徽章（放在图标上面，醒目居中）
    2. 中部：放大矢量灾害大图标
    3. 下部：灾害标题【XX红色预警】（居中，绝不重叠）
    """
    hazard = str(block.get("hazard") or ctx.resolve(block.get("hazard_template") or "") or "rainstorm")
    type_name = str(block.get("type_name") or ctx.resolve(block.get("type_name_template") or "") or "气象灾害")
    level = str(block.get("level") or ctx.resolve(block.get("level_template") or "") or "黄色")

    clean_level = level.replace("预警", "").strip()
    is_red = any(k in level for k in ("红", "RED", "橙", "ORANGE", "i级", "ii级"))
    fg_col = ctx.resolve_color({"color": block.get("color", "black")})
    acc_col = ctx.color_index("red") if (is_red and ctx.colors >= 3) else EINK_FG

    # ─────────────────────────────────────────────────────────────
    # 1. 顶部：当前生效级别指示徽章（放置在图标正上方）
    # ─────────────────────────────────────────────────────────────
    if "红" in level:
        badge_text = "红色预警 · I级 特别严重"
        badge_red = True
    elif "橙" in level:
        badge_text = "橙色预警 · II级 严重"
        badge_red = True
    elif "黄" in level:
        badge_text = "黄色预警 · III级 较重"
        badge_red = False
    elif "蓝" in level:
        badge_text = "蓝色预警 · IV级 一般"
        badge_red = False
    else:
        badge_text = f"{clean_level}预警"
        badge_red = False

    badge_font_size = max(10, int(11 * ctx.scale))
    badge_font = load_font("noto_serif_bold", badge_font_size)
    bb = safe_font_bbox(badge_font, badge_text)
    bw = bb[2] - bb[0]
    bh = max(badge_font_size, bb[3] - bb[1])

    pad_x = int(10 * ctx.scale)
    pad_y = int(3 * ctx.scale)
    badge_w = bw + pad_x * 2
    badge_h = bh + pad_y * 2
    badge_x = ctx.x_offset + (ctx.available_width - badge_w) // 2

    bg_color = ctx.color_index("red") if (badge_red and ctx.colors >= 3) else EINK_FG
    _draw_rounded_rect(ctx.draw, [(badge_x, ctx.y), (badge_x + badge_w, ctx.y + badge_h)], radius=int(3 * ctx.scale), fill=bg_color)
    ctx.draw.text((badge_x + pad_x, ctx.y + pad_y), badge_text, fill=EINK_BG, font=badge_font)

    ctx.y += badge_h + int(8 * ctx.scale)

    # ─────────────────────────────────────────────────────────────
    # 2. 中部：放大矢量灾害大图标（位于徽章下方）
    # ─────────────────────────────────────────────────────────────
    raw_icon_size = block.get("icon_size", 56)
    icon_size = max(34, int(raw_icon_size * ctx.scale))
    if ctx.screen_h <= 160:
        icon_size = 32

    icon_cx = ctx.x_offset + ctx.available_width // 2
    icon_cy = ctx.y + icon_size // 2
    draw_disaster_vector_icon(ctx.draw, hazard, icon_cx, icon_cy, size=icon_size, color=fg_col, accent_color=acc_col)
    ctx.y += icon_size + int(8 * ctx.scale)

    # ─────────────────────────────────────────────────────────────
    # 3. 下部：居中灾害名称【暴雨红色预警】（位于图标下方，绝不重叠）
    # ─────────────────────────────────────────────────────────────
    if clean_level and clean_level not in type_name:
        title_text = f"【{type_name}{clean_level}预警】"
    elif "预警" not in type_name:
        title_text = f"【{type_name}预警】"
    else:
        title_text = f"【{type_name}】"

    title_font_size = int(block.get("title_font_size", 18) * ctx.scale)
    title_font = load_font("noto_serif_bold", title_font_size)
    tb = safe_font_bbox(title_font, title_text)
    tw = tb[2] - tb[0]
    th = max(title_font_size, tb[3] - tb[1])
    title_x = ctx.x_offset + (ctx.available_width - tw) // 2
    ctx.draw.text((title_x, ctx.y), title_text, fill=EINK_FG, font=title_font)

    ctx.y += th + int(block.get("margin_bottom", 8) * ctx.scale)


@register_block("disaster_publisher_bar")
def render_disaster_publisher_bar(ctx: RenderContext, block: dict) -> None:
    """发布单位与发布时间，位于最下层。"""
    sender = str(block.get("sender") or ctx.resolve(block.get("sender_template") or "") or "国家突发事件预警信息发布中心")
    pub_time = str(block.get("time") or ctx.resolve(block.get("time_template") or "") or "")
    margin_x = int(block.get("margin_x", 12) * ctx.scale)

    bar_h = int(18 * ctx.scale)
    # 保证在最下层：若有空余高度则自动推至底部
    bottom_y = ctx.footer_top - bar_h - 2 if ctx.footer_top > 0 else (ctx.screen_h - bar_h - 4)
    if bottom_y > ctx.y:
        ctx.y = bottom_y

    x0 = ctx.x_offset + margin_x
    x1 = ctx.x_offset + ctx.available_width - margin_x

    ctx.draw.line([(x0, ctx.y), (x1, ctx.y)], fill=EINK_FG, width=1)
    ctx.y += int(3 * ctx.scale)

    font = load_font("noto_serif_regular", max(8, int(9 * ctx.scale)))
    left_str = f"发布单位：{sender}"
    right_str = f"发布时间：{pub_time}" if pub_time else ""

    ctx.draw.text((x0, ctx.y), left_str, fill=EINK_FG, font=font)
    if right_str:
        rb = safe_font_bbox(font, right_str)
        rw = rb[2] - rb[0]
        ctx.draw.text((x1 - rw, ctx.y), right_str, fill=EINK_FG, font=font)

    ctx.y += bar_h

