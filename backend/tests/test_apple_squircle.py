"""
测试面向苹果级圆角矩形 (Apple-Style Squircle / Superellipse) 的墨水屏精益绘制算法：
1. 墨水屏二值点阵上平滑超椭圆曲率 (G2 连续平滑无折角)
2. 相比粗暴圆弧，在小尺寸卡片和徽标中消除台阶锯齿
"""
from PIL import Image, ImageDraw
import pytest
from core.patterns.utils import draw_apple_squircle


def test_draw_apple_squircle_renders_smooth_border():
    img = Image.new("1", (100, 100), 1)
    draw = ImageDraw.Draw(img)

    # 绘制一个 80x40 的苹果平滑微曲率胶囊矩形
    draw_apple_squircle(draw, [10, 10, 90, 50], radius=12, fill=None, outline=0, width=1)

    # 验证矩形中心仍为白背景，且边界四角均有平滑像素连线
    assert img.getpixel((50, 30)) == 1
    # 验证边框像素被正确光栅化
    assert img.getpixel((10, 30)) == 0
    assert img.getpixel((90, 30)) == 0


def test_draw_apple_squircle_filled():
    img = Image.new("1", (100, 100), 1)
    draw = ImageDraw.Draw(img)

    # 绘制实心平滑圆角矩形 (Badge / 卡片背景)
    draw_apple_squircle(draw, [10, 10, 90, 50], radius=10, fill=0)

    # 验证中心与内部完全填充为黑
    assert img.getpixel((50, 30)) == 0
    # 验证外部角落未被误填
    assert img.getpixel((5, 5)) == 1


def test_render_card_with_apple_squircle():
    from core.blocks.context import RenderContext
    from core.blocks.layout import render_card

    img = Image.new("1", (200, 200), 1)
    draw = ImageDraw.Draw(img)
    ctx = RenderContext(
        draw=draw,
        img=img,
        content={"title": "Apple Card"},
        screen_w=200,
        screen_h=200,
        y=10,
        x_offset=0,
        available_width=200,
        colors=2,
    )
    block = {
        "type": "card",
        "border": "solid",
        "radius": 10,
        "padding": 5,
        "margin_x": 10,
        "children": [
            {"type": "text", "text": "Card Content"},
        ],
    }
    render_card(ctx, block)
    # 验证卡片绘制完成后 y 坐标向下推移
    assert ctx.y > 10
    # 验证边框像素被绘制 (例如外轮廓处)
    assert img.getpixel((10, 10)) == 0


def test_render_flex_row_with_apple_squircle_background():
    from core.blocks.context import RenderContext
    from core.blocks.layout import render_flex_row

    img = Image.new("1", (200, 200), 1)
    draw = ImageDraw.Draw(img)
    ctx = RenderContext(
        draw=draw,
        img=img,
        content={"tag1": "Tag A", "tag2": "Tag B"},
        screen_w=200,
        screen_h=200,
        y=20,
        x_offset=0,
        available_width=200,
        colors=2,
    )
    block = {
        "type": "flex_row",
        "bg_color": "black",
        "radius": 6,
        "items": [
            {"type": "text", "text": "Tag A", "color": "white"},
            {"type": "text", "text": "Tag B", "color": "white"},
        ],
    }
    render_flex_row(ctx, block)
    assert ctx.y > 20
    # 验证内部区域被黑色底板填充
    assert img.getpixel((100, 22)) == 0
