import pytest
from PIL import Image, ImageDraw
import numpy as np

from core.patterns.utils import has_cjk, wrap_text, load_font, EINK_BG, EINK_FG
from core.config import EINK_4COLOR_PALETTE
from core.json_renderer import RenderContext, _render_block


def test_has_cjk_supports_japanese_kana_and_symbols():
    # Chinese
    assert has_cjk("这是中文测试") is True
    # Japanese Hiragana
    assert has_cjk("あかり") is True
    assert has_cjk("松永あかり(松永明里)") is True
    # Japanese Katakana
    assert has_cjk("カタカナ") is True
    assert has_cjk("アニメ") is True
    # Japanese / CJK brackets and punctuation
    assert has_cjk("「引用括弧」") is True
    assert has_cjk("『二重鉤括弧』") is True
    # Pure ASCII
    assert has_cjk("English text with numbers 1234567890") is False


def test_wrap_text_keeps_urls_and_words_intact():
    font = load_font("noto_serif_regular", 13)
    text = "這是事務所「Y’s Entertainment」為經紀人設立的X帳號(https://x.com/Ysent50）。"
    lines = wrap_text(text, font, 368)

    # Verify that https:// is never split across line breaks
    for line in lines:
        if "http" in line:
            assert "https://" in line or "http://" in line
            assert not line.endswith("https")
            assert not line.startswith("://")

    # Verify Kinsoku Shori: closing punctuation should not sit alone at start of line
    not_start_chars = set("，。、！？：；）)]}」』】”’…⋯—～~")
    for line in lines[1:]:
        assert line[0] not in not_start_chars


def test_render_text_never_crosses_footer_horizontal_line():
    # 400x300 canvas with a footer divider line at y=270
    w, h = 400, 300
    footer_h = 30  # footer_top = 270
    img = Image.new("P", (w, h), 1)
    img.putpalette(EINK_4COLOR_PALETTE)
    draw = ImageDraw.Draw(img)

    ctx = RenderContext(
        draw=draw,
        img=img,
        content={},
        screen_w=w,
        screen_h=h,
        y=202,  # starts where an image block ended
        available_width=w,
        colors=3,
        footer_height=footer_h,
    )

    long_summary = (
        "這是事務所「Y’s Entertainment」為經紀人設立的X帳號(https://x.com/Ysent50）。 "
        "很多經紀公司都會讓馬內甲擔任宣傳的工作，不過看看這個帳號的自我介紹，有個大家應該都不認識的名字「白石くれあ(白石來愛)」： "
        "然後順藤摸瓜，你很快就能找到这位女優的..."
    )

    text_block = {
        "type": "text",
        "text": long_summary,
        "font_size": 13,
        "line_height": 19,
        "align": "left",
        "margin_x": 16,
        "max_lines": 4,
    }

    _render_block(ctx, text_block)

    # Draw the footer line at y=270
    draw.line([(0, 270), (w, 270)], fill=EINK_FG, width=1)

    arr = np.array(img)
    # Rows 265 to 269 should be clean buffer (0 content pixels)
    for y in range(265, 270):
        assert (arr[y] != 1).sum() == 0, f"Row {y} should have 0 pixels, but had {(arr[y] != 1).sum()} (text crossed into footer!)"

    # Row 271 to 275 should also have 0 content pixels
    for y in range(271, 275):
        assert (arr[y] != 1).sum() == 0, f"Row {y} should have 0 pixels, but had {(arr[y] != 1).sum()}"
