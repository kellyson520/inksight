"""
InkSight 扩充排版组件库 6：阅读创作、诗词书摘与排版装饰边框 (Typography & Editorial)
包含：
76. book_spine_card: 拟真书脊立体排版卡片
77. chapter_ribbon: 章节标题书签丝带
78. drop_cap_paragraph: 首字下沉大写段落
79. poetic_couplet_box: 对联/双行竖排律诗框
80. footnote_reference: 脚注标号与引用解释行
81. author_signature_stamp: 作者落款与方印小章
82. reading_progress_dots: 阅读章节页码点阵
83. pull_quote_banner: 大号引文拉页高亮条
84. golden_ratio_split: 黄金比例 0.618 分割双栏
85. vintage_header_ornament: 复古欧式排版卷草纹顶栏
86. gothic_corner_frame: 哥特式四角直角花边框
87. ticket_stub_coupon: 票根与锯齿虚线优惠券卡
88. newspaper_headline_deck: 报纸三层头条大字副题排版
89. manuscript_grid_paper: 原稿纸方格对齐文本
90. dictionary_phonetic_entry: 词典音标与词性词源条目
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
    wrap_text,
)
from .context import RenderContext
from .registry import register_block

logger = logging.getLogger(__name__)


def _draw_box(draw: ImageDraw.ImageDraw, bbox: tuple[int, int, int, int], outline=EINK_FG, fill=None, width=1):
    draw.rectangle(bbox, outline=outline, fill=fill, width=width)


@register_block("book_spine_card")
def render_book_spine_card(ctx: RenderContext, block: dict) -> None:
    """书脊立体排版卡片。"""
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 6) * ctx.scale)
    title = str(block.get("title", "瓦尔登湖"))
    author = str(block.get("author", "梭罗"))
    x = ctx.x_offset + margin_x
    y = ctx.y
    w = ctx.available_width - margin_x * 2

    _draw_box(ctx.draw, (x, y, x + w, y + 26), outline=EINK_FG, width=1)
    # 书脊左侧双线
    ctx.draw.line((x + 6, y, x + 6, y + 26), fill=EINK_FG, width=1)
    ctx.draw.line((x + 9, y, x + 9, y + 26), fill=EINK_FG, width=1)

    font_t = load_font("noto_serif_bold", int(10 * ctx.scale))
    font_a = load_font("noto_serif_regular", int(8 * ctx.scale))
    ctx.draw.text((x + 16, y + 3), title, fill=EINK_FG, font=font_t)
    ctx.draw.text((x + 16, y + 14), f"[{author} 著]", fill=EINK_FG, font=font_a)
    ctx.y = y + 28 + margin_bottom


@register_block("chapter_ribbon")
def render_chapter_ribbon(ctx: RenderContext, block: dict) -> None:
    """章节丝带书签。"""
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 4) * ctx.scale)
    chapter = str(block.get("chapter", "CHAPTER IV · 寂寞"))
    x = ctx.x_offset + margin_x
    y = ctx.y

    font = load_font("noto_serif_bold", int(9 * ctx.scale))
    tb = safe_font_bbox(font, chapter)
    bw = (tb[2] - tb[0]) + 16
    _draw_box(ctx.draw, (x, y, x + bw, y + 14), fill=EINK_FG)
    ctx.draw.text((x + 8, y + 1), chapter, fill=EINK_BG, font=font)
    ctx.y = y + 16 + margin_bottom


@register_block("drop_cap_paragraph")
def render_drop_cap_paragraph(ctx: RenderContext, block: dict) -> None:
    """首字下沉段落。"""
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 6) * ctx.scale)
    text = str(block.get("text", "时间只是我垂钓的溪。我喝溪水，我喝的时候，我看到沙底，发现了它是多么浅。"))
    first_char = text[:1]
    rest_text = text[1:]
    x = ctx.x_offset + margin_x
    y = ctx.y
    w = ctx.available_width - margin_x * 2

    font_cap = load_font("noto_serif_bold", int(22 * ctx.scale))
    font_body = load_font("noto_serif_regular", int(9 * ctx.scale))

    # 首字下沉方框
    _draw_box(ctx.draw, (x, y, x + 26, y + 26), fill=EINK_FG)
    tb = safe_font_bbox(font_cap, first_char)
    ctx.draw.text((x + (26 - (tb[2]-tb[0]))//2, y + (26 - (tb[3]-tb[1]))//2 - tb[1]), first_char, fill=EINK_BG, font=font_cap)

    # 旁边文本
    lines = wrap_text(rest_text, font_body, w - 32)
    cy = y
    for ln in lines[:3]:
        ctx.draw.text((x + 32, cy), ln, fill=EINK_FG, font=font_body)
        cy += 11

    ctx.y = max(y + 28, cy) + margin_bottom


@register_block("poetic_couplet_box")
def render_poetic_couplet_box(ctx: RenderContext, block: dict) -> None:
    """诗词律绝排版框。"""
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 6) * ctx.scale)
    line1 = str(block.get("line1", "明月松间照"))
    line2 = str(block.get("line2", "清泉石上流"))
    x = ctx.x_offset + margin_x
    y = ctx.y
    w = ctx.available_width - margin_x * 2

    _draw_box(ctx.draw, (x, y, x + w, y + 32), outline=EINK_FG, width=1)
    font = load_font("noto_serif_regular", int(10 * ctx.scale))
    tb1 = safe_font_bbox(font, line1)
    tb2 = safe_font_bbox(font, line2)
    cx = x + w // 2
    ctx.draw.text((cx - (tb1[2]-tb1[0])//2, y + 4), line1, fill=EINK_FG, font=font)
    ctx.draw.text((cx - (tb2[2]-tb2[0])//2, y + 17), line2, fill=EINK_FG, font=font)
    ctx.y = y + 34 + margin_bottom


@register_block("footnote_reference")
def render_footnote_reference(ctx: RenderContext, block: dict) -> None:
    """脚注标号引用行。"""
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 4) * ctx.scale)
    note = str(block.get("note", "[1] 选自《瓦尔登湖·余音》，徐迟译本。"))
    x = ctx.x_offset + margin_x
    y = ctx.y

    font = load_font("noto_serif_regular", int(8 * ctx.scale))
    ctx.draw.line((x, y, x + 30, y), fill=EINK_FG, width=1)
    ctx.draw.text((x, y + 3), note, fill=EINK_FG, font=font)
    ctx.y = y + 14 + margin_bottom


@register_block("author_signature_stamp")
def render_author_signature_stamp(ctx: RenderContext, block: dict) -> None:
    """作者落款印章。"""
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 4) * ctx.scale)
    author = str(block.get("author", "亨利·戴维·梭罗"))
    x = ctx.x_offset + margin_x
    y = ctx.y
    w = ctx.available_width - margin_x * 2

    font_a = load_font("noto_serif_regular", int(9 * ctx.scale))
    tb = safe_font_bbox(font_a, author)
    aw = tb[2] - tb[0]
    ax = x + w - aw - 24
    ctx.draw.text((ax, y + 2), author, fill=EINK_FG, font=font_a)
    # 印章方块
    _draw_box(ctx.draw, (x + w - 18, y, x + w - 2, y + 16), outline=EINK_FG, width=1)
    font_s = load_font("noto_serif_bold", int(8 * ctx.scale))
    ctx.draw.text((x + w - 14, y + 2), "印", fill=EINK_FG, font=font_s)
    ctx.y = y + 18 + margin_bottom


@register_block("reading_progress_dots")
def render_reading_progress_dots(ctx: RenderContext, block: dict) -> None:
    """阅读章节进度点阵。"""
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 4) * ctx.scale)
    cur = int(block.get("cur", 6))
    total = int(block.get("total", 12))
    x = ctx.x_offset + margin_x
    y = ctx.y

    font = load_font("noto_serif_regular", int(8 * ctx.scale))
    ctx.draw.text((x, y), f"PAGES: {cur}/{total}", fill=EINK_FG, font=font)
    sx = x + 70
    for i in range(total):
        dx = sx + i * 7
        fill = EINK_FG if i < cur else None
        ctx.draw.ellipse((dx, y + 2, dx + 4, y + 6), outline=EINK_FG, fill=fill)
    ctx.y = y + 12 + margin_bottom


@register_block("pull_quote_banner")
def render_pull_quote_banner(ctx: RenderContext, block: dict) -> None:
    """大号拉页引言条。"""
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 6) * ctx.scale)
    quote = str(block.get("quote", "无论你的生活如何卑微，都要面对它，度过它。"))
    x = ctx.x_offset + margin_x
    y = ctx.y
    w = ctx.available_width - margin_x * 2

    # 左右双立柱
    ctx.draw.line((x, y, x, y + 24), fill=EINK_FG, width=3)
    font = load_font("noto_serif_bold", int(9 * ctx.scale))
    lines = wrap_text(quote, font, w - 16)
    cy = y
    for ln in lines[:2]:
        ctx.draw.text((x + 8, cy), ln, fill=EINK_FG, font=font)
        cy += 12
    ctx.y = max(y + 24, cy) + margin_bottom


@register_block("golden_ratio_split")
def render_golden_ratio_split(ctx: RenderContext, block: dict) -> None:
    """黄金比例 0.618 分割线。"""
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 4) * ctx.scale)
    x = ctx.x_offset + margin_x
    y = ctx.y
    w = ctx.available_width - margin_x * 2

    split_x = int(x + w * 0.618)
    ctx.draw.line((x, y, x + w, y), fill=EINK_FG, width=1)
    ctx.draw.ellipse((split_x - 2, y - 2, split_x + 2, y + 2), fill=EINK_FG)
    ctx.y = y + 5 + margin_bottom


@register_block("vintage_header_ornament")
def render_vintage_header_ornament(ctx: RenderContext, block: dict) -> None:
    """复古卷草纹顶栏。"""
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 4) * ctx.scale)
    title = str(block.get("title", "LITERARY DIGEST"))
    x = ctx.x_offset + margin_x
    y = ctx.y
    w = ctx.available_width - margin_x * 2
    cx = x + w // 2

    font = load_font("noto_serif_bold", int(9 * ctx.scale))
    tb = safe_font_bbox(font, title)
    tw = tb[2] - tb[0]
    ctx.draw.text((cx - tw // 2, y), title, fill=EINK_FG, font=font)
    # 左右花边线条
    ctx.draw.line((x, y + 5, cx - tw // 2 - 8, y + 5), fill=EINK_FG, width=1)
    ctx.draw.line((cx + tw // 2 + 8, y + 5, x + w, y + 5), fill=EINK_FG, width=1)
    ctx.y = y + 13 + margin_bottom


@register_block("gothic_corner_frame")
def render_gothic_corner_frame(ctx: RenderContext, block: dict) -> None:
    """哥特式折角框。"""
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 6) * ctx.scale)
    x = ctx.x_offset + margin_x
    y = ctx.y
    w = ctx.available_width - margin_x * 2
    h = 30

    _draw_box(ctx.draw, (x, y, x + w, y + h), outline=EINK_FG, width=1)
    # 四个内折角装饰
    for cx, cy in [(x+4, y+4), (x+w-4, y+4), (x+4, y+h-4), (x+w-4, y+h-4)]:
        ctx.draw.line((cx - 2, cy, cx + 2, cy), fill=EINK_FG, width=1)
        ctx.draw.line((cx, cy - 2, cx, cy + 2), fill=EINK_FG, width=1)
    ctx.y = y + h + margin_bottom


@register_block("ticket_stub_coupon")
def render_ticket_stub_coupon(ctx: RenderContext, block: dict) -> None:
    """票根优惠券锯齿卡。"""
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 6) * ctx.scale)
    code = str(block.get("code", "PASS · 2026-VIP"))
    x = ctx.x_offset + margin_x
    y = ctx.y
    w = ctx.available_width - margin_x * 2
    h = 24

    _draw_box(ctx.draw, (x, y, x + w, y + h), outline=EINK_FG, width=1)
    # 左右锯齿半圆缺口
    ctx.draw.ellipse((x - 4, y + 8, x + 4, y + 16), fill=EINK_BG, outline=EINK_FG)
    ctx.draw.ellipse((x + w - 4, y + 8, x + w + 4, y + 16), fill=EINK_BG, outline=EINK_FG)

    font = load_font("noto_serif_bold", int(9 * ctx.scale))
    ctx.draw.text((x + 16, y + 5), code, fill=EINK_FG, font=font)
    ctx.y = y + h + margin_bottom


@register_block("newspaper_headline_deck")
def render_newspaper_headline_deck(ctx: RenderContext, block: dict) -> None:
    """报纸头条三层大字排版。"""
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 6) * ctx.scale)
    deck = str(block.get("deck", "THE INKSIGHT CHRONICLE"))
    head = str(block.get("head", "BREAKTHROUGH ANNOUNCED"))
    x = ctx.x_offset + margin_x
    y = ctx.y

    font_d = load_font("noto_serif_regular", int(8 * ctx.scale))
    font_h = load_font("noto_serif_bold", int(14 * ctx.scale))
    ctx.draw.text((x, y), deck, fill=EINK_FG, font=font_d)
    ctx.draw.text((x, y + 11), head, fill=EINK_FG, font=font_h)
    ctx.y = y + 28 + margin_bottom


@register_block("manuscript_grid_paper")
def render_manuscript_grid_paper(ctx: RenderContext, block: dict) -> None:
    """稿纸方格对齐文本。"""
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 6) * ctx.scale)
    chars = str(block.get("chars", "文以载道修身明德"))[:8]
    x = ctx.x_offset + margin_x
    y = ctx.y

    font = load_font("noto_serif_regular", int(10 * ctx.scale))
    for i, ch in enumerate(chars):
        bx = x + i * 16
        _draw_box(ctx.draw, (bx, y, bx + 14, y + 14), outline=EINK_FG, width=1)
        tb = safe_font_bbox(font, ch)
        ctx.draw.text((bx + (14 - (tb[2]-tb[0]))//2, y + (14 - (tb[3]-tb[1]))//2 - tb[1]), ch, fill=EINK_FG, font=font)
    ctx.y = y + 16 + margin_bottom


@register_block("dictionary_phonetic_entry")
def render_dictionary_phonetic_entry(ctx: RenderContext, block: dict) -> None:
    """词典音标与释义行。"""
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 4) * ctx.scale)
    word = str(block.get("word", "Epiphany"))
    ipa = str(block.get("ipa", "/ɪˈpɪfəni/"))
    pos = str(block.get("pos", "n. 顿悟，神启"))
    x = ctx.x_offset + margin_x
    y = ctx.y

    font_w = load_font("noto_serif_bold", int(10 * ctx.scale))
    font_i = load_font("noto_serif_regular", int(8 * ctx.scale))
    ctx.draw.text((x, y), word, fill=EINK_FG, font=font_w)
    ctx.draw.text((x + 70, y + 1), f"{ipa} · {pos}", fill=EINK_FG, font=font_i)
    ctx.y = y + 14 + margin_bottom
