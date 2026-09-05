"""
测试：抖动自愈降级与布局边界防溢出保护 (Dither Fallback & Layout Boundary Tests)
"""
from __future__ import annotations

import pytest
from PIL import Image, ImageDraw

from core.blocks.context import RenderContext
from core.blocks.layout import render_card, render_two_column
from core.native_dither import atkinson_bw, atkinson_palette, _fallback_atkinson_bw, _fallback_palette


def test_dither_fallback_functions_direct():
    """验证纯 Python / Pillow 抖动降级函数生成合法调色板与尺寸。"""
    rgb = Image.new("RGB", (100, 100), (200, 50, 50))
    gray = rgb.convert("L")

    # 测试单色降级
    bw = _fallback_atkinson_bw(gray)
    assert bw.size == (100, 100)
    assert bw.mode == "1"

    # 测试 3 色降级
    pal3 = _fallback_palette(rgb, 3)
    assert pal3.size == (100, 100)
    assert pal3.mode == "P"

    # 测试 4 色降级
    pal4 = _fallback_palette(rgb, 4)
    assert pal4.size == (100, 100)
    assert pal4.mode == "P"


def test_atkinson_functions_end_to_end():
    """验证主 entry 函数正常返回图像且不抛出异常。"""
    rgb = Image.new("RGB", (80, 60), (100, 150, 220))
    gray = rgb.convert("L")

    bw = atkinson_bw(gray)
    assert bw.size == (80, 60)

    p4 = atkinson_palette(rgb, 4)
    assert p4.size == (80, 60)
    assert p4.mode == "P"


def test_two_column_overflow_boundary_protection():
    """验证两个过长的列不会绘制穿透到 footer 之下。"""
    img = Image.new("1", (400, 300), 1)
    draw = ImageDraw.Draw(img)
    ctx = RenderContext(
        draw=draw,
        img=img,
        content={},
        screen_w=400,
        screen_h=300,
        y=200,
        footer_height=30,
        colors=2,
    )
    # footer_top 为 270，添加许多高块
    block = {
        "type": "two_column",
        "left_blocks": [{"type": "spacer", "height": 60} for _ in range(5)],
        "right_blocks": [{"type": "spacer", "height": 60} for _ in range(5)],
    }
    # 不应该 crash，且两列执行受 footer_top 保护
    render_two_column(ctx, block)
    assert ctx.y > 200


def test_card_boundary_overflow_protection():
    """验证卡片的高度不会穿透 footer_top。"""
    img = Image.new("1", (400, 300), 1)
    draw = ImageDraw.Draw(img)
    ctx = RenderContext(
        draw=draw,
        img=img,
        content={},
        screen_w=400,
        screen_h=300,
        y=220,
        footer_height=30,
        colors=2,
    )
    block = {
        "type": "card",
        "children": [{"type": "spacer", "height": 80} for _ in range(3)],
    }
    render_card(ctx, block)
    assert ctx.y > 220


def test_wrap_text_cjk_and_extreme_widths():
    """验证 wrap_text 在极窄宽度或中日韩紧凑标点场景下的鲁棒性。"""
    from core.patterns.utils import load_font, wrap_text
    font = load_font("noto_serif_regular", 14)

    # 极窄宽度不会陷入死循环或崩溃
    lines = wrap_text("测试极窄宽度的文本折行能力！", font, max_width=5)
    assert len(lines) > 0

    # 标点符号避头法则测试：句号感叹号不单独留在新一行首位
    lines_cjk = wrap_text("你好，世界！", font, max_width=60)
    for line in lines_cjk:
        if len(line) == 1:
            assert line[0] not in "，。！"


def test_two_column_ultra_narrow_fallback():
    """验证在 col_avail 极窄时两栏自动安全退化为单栏。"""
    img = Image.new("1", (400, 300), 1)
    draw = ImageDraw.Draw(img)
    ctx = RenderContext(
        draw=draw,
        img=img,
        content={},
        screen_w=400,
        screen_h=300,
        y=10,
        available_width=60,  # 极窄宽度
        colors=2,
    )
    block = {
        "type": "two_column",
        "margin_x": 20,
        "gap": 15,
        "left_blocks": [{"type": "spacer", "height": 10}],
        "right_blocks": [{"type": "spacer", "height": 15}],
    }
    render_two_column(ctx, block)
    # 退化后两列顺序渲染，y 增加 10 + 15 = 25
    assert ctx.y == 35
