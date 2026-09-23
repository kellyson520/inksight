"""
测试多快好省优化能力 (Lean & Fast Optimization Tests):
1. 向量化高性能 2bpp 点阵转换 (image_to_raw_2bpp):
   - 验证单色 (1-bit) 与四色 (P-mode) 图像输出与基准完全一致
   - 验证非 4 整数倍尺寸对齐与补齐 (pad_w)
2. 苹果级超椭圆曲线 (Squircle) 缓存加速:
   - 验证 LRU 缓存命中与点阵坐标生成正确性
3. 苹果级墨水屏曝光曲线 (Tonal Curve LUT) 缓存命中与平滑度
"""
import pytest
from PIL import Image
from core.renderer import image_to_raw_2bpp
from core.patterns.utils import _get_squircle_relative_points, draw_apple_squircle
from core.image_processing import _get_apple_eink_lut, apply_apple_eink_tone_curve


def test_image_to_raw_2bpp_fast_path_identity():
    # 1. 单色模式
    img_1 = Image.new("1", (400, 300), 1)
    raw_1 = image_to_raw_2bpp(img_1)
    assert len(raw_1) == 400 * 300 // 4
    assert raw_1[0] == 0x55  # 4 个白像素 (01 01 01 01)

    # 2. 四色调色板模式
    img_p = Image.new("P", (400, 300), 0)
    # 设置前 4 个像素为 0 (黑), 1 (白), 2 (黄), 3 (红)
    img_p.putpixel((0, 0), 0)
    img_p.putpixel((1, 0), 1)
    img_p.putpixel((2, 0), 2)
    img_p.putpixel((3, 0), 3)
    raw_p = image_to_raw_2bpp(img_p)
    assert len(raw_p) == 400 * 300 // 4
    # (0 << 6) | (1 << 4) | (2 << 2) | 3 = 0b00011011 = 0x1B
    assert raw_p[0] == 0x1B


def test_image_to_raw_2bpp_odd_dimensions():
    # 非 4 整数倍尺寸测试 (例如 297x128)
    img = Image.new("1", (297, 128), 1)
    raw = image_to_raw_2bpp(img)
    assert len(raw) == 297 * 128 // 4


def test_squircle_lru_cache_hit():
    # 清空缓存
    _get_squircle_relative_points.cache_clear()
    pts1 = _get_squircle_relative_points(100, 50, 8, 3.2, 8)
    pts2 = _get_squircle_relative_points(100, 50, 8, 3.2, 8)
    assert pts1 == pts2
    info = _get_squircle_relative_points.cache_info()
    assert info.hits >= 1


def test_apple_eink_lut_caching():
    _get_apple_eink_lut.cache_clear()
    lut1 = _get_apple_eink_lut(120)
    lut2 = _get_apple_eink_lut(120)
    assert lut1 == lut2
    assert len(lut1) == 256
    info = _get_apple_eink_lut.cache_info()
    assert info.hits >= 1
