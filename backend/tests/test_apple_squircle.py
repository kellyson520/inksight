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
