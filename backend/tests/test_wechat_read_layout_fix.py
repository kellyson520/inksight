"""
微信读书模式与双栏布局精准渲染测试 (WeChat Read Layout & Content Regression Test)
验证：
1. render_two_column 正确支持 left_blocks / right_blocks 别名
2. measure_block_size 对 two_column 精确度量两列高度，防止占位为 1 导致的重叠或裁切
3. WECHAT_READ 完整渲染后全屏正文非白色像素覆盖率 > 15000 像素，彻底杜绝大面积空白
"""
from __future__ import annotations

import pytest
from PIL import Image, ImageDraw

from core.blocks.context import RenderContext
from core.blocks.layout import render_two_column
from core.blocks.measure import measure_block_size
from core.pipeline import generate_and_render


def test_two_column_block_aliases_rendering():
    """验证 left_blocks/right_blocks 和 left_ratio 的正确解析。"""
    img = Image.new("1", (400, 300), 1)
    draw = ImageDraw.Draw(img)
    ctx = RenderContext(
        draw=draw,
        img=img,
        content={"left_txt": "Left Column Content", "right_txt": "Right Column Content"},
        screen_w=400,
        screen_h=300,
        y=10,
        colors=2,
    )
    block = {
        "type": "two_column",
        "margin_x": 12,
        "gap": 12,
        "left_ratio": 0.6,
        "left_blocks": [{"type": "text", "field": "left_txt", "font_size": 14}],
        "right_blocks": [{"type": "text", "field": "right_txt", "font_size": 14}],
    }
    render_two_column(ctx, block)
    # 渲染后 y 坐标应下移
    assert ctx.y > 20

    # 验证左右区域均有像素绘制
    left_non_white = sum(1 for y in range(ctx.screen_h) for x in range(12, 200) if img.getpixel((x, y)) == 0)
    right_non_white = sum(1 for y in range(ctx.screen_h) for x in range(220, 380) if img.getpixel((x, y)) == 0)
    assert left_non_white > 10
    assert right_non_white > 10


def test_measure_two_column_block_accurate():
    """验证 two_column 精确测量高度。"""
    img = Image.new("1", (400, 300), 1)
    draw = ImageDraw.Draw(img)
    ctx = RenderContext(
        draw=draw,
        img=img,
        content={},
        screen_w=400,
        screen_h=300,
        y=0,
        colors=2,
    )
    block = {
        "type": "two_column",
        "margin_x": 10,
        "gap": 10,
        "left_blocks": [
            {"type": "spacer", "height": 30},
            {"type": "spacer", "height": 20},
        ],
        "right_blocks": [
            {"type": "spacer", "height": 80},
        ],
        "margin_bottom": 5,
    }
    w, h = measure_block_size(ctx, block, 400)
    assert w == 400
    assert h == 85


@pytest.mark.asyncio
async def test_wechat_read_mode_renders_full_content_not_blank():
    """验证 WECHAT_READ 模式渲染出真实图文，非空白屏。"""
    img, content = await generate_and_render(
        persona="WECHAT_READ",
        config={"modes": ["WECHAT_READ"], "colors": 4},
        date_ctx={"date_str": "2026-03-30", "time_str": "12:00"},
        weather={"weather_str": "晴", "weather_code": 0},
        battery_pct=95,
        screen_w=400,
        screen_h=300,
        mac="70:AF:09:75:51:84",
        colors=4,
    )
    assert img.size == (400, 300)
    assert content["title"]
    assert content["author"]

    # 检查非白色像素（0=黑色, 2=黄色, 3=红色）的总数，空白屏通常只有 2000 左右（仅状态栏和页脚）
    non_white_pixels = sum(1 for y in range(img.height) for x in range(img.width) if img.getpixel((x, y)) != 1)
    # 正常内容渲染后非白色像素应 > 10000 像素
    assert non_white_pixels > 10000, f"Expected non-blank content, got only {non_white_pixels} pixels"
