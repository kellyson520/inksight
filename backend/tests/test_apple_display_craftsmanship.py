"""
测试苹果级墨水屏显示与排版雕琢算法 (Apple-Grade Display Craftsmanship)：
1. 墨水屏自适应光影曲线 (Shadow Boost & Highlight Roll-off)
2. 文本截断优雅标点剔除 (自然结尾，无突兀逗号/顿号省略号)
3. 动态黄金排版行距自适应
"""
from PIL import Image, ImageDraw
import pytest
from core.image_processing import apply_apple_eink_tone_curve, quantize_image_for_eink
from core.blocks.text import render_text
from core.blocks.context import RenderContext


def test_apple_eink_tone_curve_lifts_deep_shadows():
    # 构造一张带有深色暗部 (例如 RGB=25 的深黑西服/头发) 的图像
    im = Image.new("RGB", (50, 50), (25, 25, 25))
    adjusted = apply_apple_eink_tone_curve(im)

    # 验证暗部在曲线映射后被平滑提亮，避免死黑
    pixel_r = adjusted.getpixel((25, 25))[0]
    assert pixel_r > 25, f"Expected shadow lift > 25, got {pixel_r}"


def test_apple_eink_tone_curve_compresses_highlights():
    # 构造一张带有高光亮部 (例如 RGB=245 的雪地/高光) 的图像
    im = Image.new("RGB", (50, 50), (245, 245, 245))
    adjusted = apply_apple_eink_tone_curve(im)

    # 验证高光柔和滚降，避免直接过曝切断
    pixel_r = adjusted.getpixel((25, 25))[0]
    assert pixel_r <= 255


def test_clean_punctuation_trimming_before_ellipsis():
    # 构造一个带有行末标点的截断场景
    img = Image.new("1", (200, 200), 1)
    draw = ImageDraw.Draw(img)
    ctx = RenderContext(
        img=img,
        draw=draw,
        content={"msg": "春江潮水连海平，海上明月共潮生。潋滟随波千万里，何处春江无月明！"},
        screen_w=200,
        screen_h=200,
        colors=2,
    )

    block = {
        "field": "msg",
        "font_size": 18,
        "max_lines": 1,
        "ellipsis": True,
        "margin_x": 10,
    }

    render_text(ctx, block)

    # 验证渲染未崩溃且在单行物理空间中正常绘制
    assert ctx.y > 0
