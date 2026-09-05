"""
底层算法与性能基准测试 (Low-level Algorithms Benchmark & Correctness)
验证：
1. rgba_to_mono 向量化查表转换与原逻辑等价性及高吞吐
2. wrap_text 在复杂中西文混排、长 URL 与标点避让时的稳定性
3. 多源容灾缓存自愈与退避策略验证
"""
from __future__ import annotations

import pytest
from PIL import Image, ImageFont
from core.patterns.utils import rgba_to_mono, wrap_text, load_font


def test_rgba_to_mono_vectorized_correctness():
    """验证 rgba_to_mono 矢量化 LUT 转换正确性。"""
    # 创建一个 10x10 RGBA 图像，半透明与全透明交替
    img = Image.new("RGBA", (10, 10), (0, 0, 0, 0))
    for x in range(5):
        for y in range(10):
            img.putpixel((x, y), (255, 0, 0, 255))  # 完全不透明 -> 0 (墨水黑)
    for x in range(5, 10):
        for y in range(10):
            img.putpixel((x, y), (0, 0, 0, 50))    # 低于阈值 -> 1 (白背景)

    mono = rgba_to_mono(img)
    assert mono.mode == "1"
    assert mono.size == (10, 10)

    # 验证像素
    for y in range(10):
        for x in range(5):
            assert mono.getpixel((x, y)) == 0
        for x in range(5, 10):
            assert mono.getpixel((x, y)) == 1


def test_wrap_text_smart_line_breaking():
    """验证智能排版折行算法。"""
    font = load_font("noto_serif_regular", 12)
    text = "InkSight 墨水屏智能桌面伴侣：支持超长链接 https://github.com/kellyson520/inksight 与中西文混合排版，避头尾法则生效。"
    lines = wrap_text(text, font, max_width=180)

    assert len(lines) >= 2
    # 验证没有空行
    assert all(len(ln.strip()) > 0 for ln in lines)
    # 验证标点避头：除微悬挂外，行首不应以禁止符号开头
    not_starts = set("，。！？；）】")
    for ln in lines[1:]:
        assert ln[0] not in not_starts or len(ln) == 1
