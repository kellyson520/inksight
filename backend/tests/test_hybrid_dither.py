"""
测试墨水屏自适应混合抖动算法 (Hybrid E-ink Dithering)
"""
from PIL import Image, ImageDraw
from core.image_processing import hybrid_dither_for_eink, quantize_image_for_eink


def test_hybrid_dither_preserves_sharp_black_text_lines():
    # 构造一张带有纯黑文字/线条和中间灰度渐变的测试图
    img = Image.new("RGB", (60, 60), (240, 240, 240))
    draw = ImageDraw.Draw(img)

    # 绘制中间连续灰度区域
    draw.rectangle([10, 10, 50, 30], fill=(128, 128, 128))

    # 绘制极细纯黑线（如文字笔画）
    draw.line([5, 40, 55, 40], fill=(0, 0, 0), width=1)

    out = hybrid_dither_for_eink(img, colors=2, edge_preserve=True)

    assert out.mode == "1"
    assert out.size == (60, 60)

    # 验证纯黑线所在的像素行没有被抖动打碎成白点，而是保持坚挺的纯黑线
    line_pixels = [out.getpixel((x, 40)) for x in range(10, 50)]
    assert all(p == 0 for p in line_pixels)


def test_hybrid_dither_quantize_flag_compatibility():
    img = Image.new("RGB", (20, 20), (100, 100, 100))
    # 通过 quantize_image_for_eink 传入 hybrid=True
    out = quantize_image_for_eink(img, colors=2, hybrid=True)
    assert out.mode == "1"
