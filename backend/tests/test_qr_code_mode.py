"""
二维码展示模式与原生渲染 Block 单元测试 (QR Code Mode & Block Tests)
"""
from __future__ import annotations

import pytest
from PIL import Image, ImageDraw
import numpy as np

from core.blocks.context import RenderContext
from core.blocks.qrcode import render_qrcode
from core.blocks.measure import measure_block_size
from core.mode_registry import get_registry
from core.pipeline import generate_and_render


def test_render_qrcode_block_direct():
    """验证原生 qrcode block 在各种设置下均能成功绘制。"""
    img = Image.new("1", (400, 300), 1)
    draw = ImageDraw.Draw(img)
    ctx = RenderContext(
        draw=draw,
        img=img,
        content={"qr_content": "https://github.com/kellyson520/inksight"},
        screen_w=400,
        screen_h=300,
        y=10,
        colors=2,
    )
    block = {
        "type": "qrcode",
        "field": "qr_content",
        "size": 120,
        "border": 1,
        "align": "center",
    }
    render_qrcode(ctx, block)
    # y 应该已经更新增加 size + margin
    assert ctx.y > 100


def test_qrcode_does_not_render_as_solid_black_when_pasting_to_palette_image():
    """彩色墨水屏二维码必须保留白色背景，不能因 P 模式 paste 变成整块黑色。"""
    img = Image.new("P", (240, 180), 1)
    img.putpalette([
        0, 0, 0,
        255, 255, 255,
        232, 176, 0,
        200, 0, 0,
    ] + [0, 0, 0] * 252)
    ctx = RenderContext(
        draw=ImageDraw.Draw(img), img=img, content={"qr_content": "https://example.com/qr"},
        screen_w=240, screen_h=180, y=10, colors=4,
    )
    render_qrcode(ctx, {"type": "qrcode", "field": "qr_content", "size": 120, "border": 2})
    crop = np.asarray(img)[10:130, 60:180]
    black_ratio = float(np.mean(crop == 0))
    white_ratio = float(np.mean(crop == 1))
    assert black_ratio < 0.6, f"QR became mostly black: {black_ratio:.3f}"
    assert white_ratio > 0.2, f"QR lost its white modules/background: {white_ratio:.3f}"


def test_measure_qrcode_block():
    """验证 qrcode block 尺寸度量。"""
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
    block = {"type": "qrcode", "size": 150, "margin_bottom": 8}
    w, h = measure_block_size(ctx, block, 400)
    assert w == 400
    assert h == 158


def test_qr_code_mode_registered():
    """验证 QR_CODE 模式被成功发现并登记在 ModeRegistry 中。"""
    registry = get_registry()
    assert "QR_CODE" in registry.get_supported_ids()


@pytest.mark.asyncio
async def test_qr_code_pipeline_rendering():
    """验证通过标准 pipeline 渲染 QR_CODE 模式。"""
    img, content = await generate_and_render(
        persona="QR_CODE",
        config={
            "modes": ["QR_CODE"],
            "mode_overrides": {
                "QR_CODE": {
                    "type": "URL",
                    "title": "测试二维码",
                    "url": "https://inksight.local/test",
                }
            },
        },
        date_ctx={"date_str": "2026-03-30", "time_str": "12:00"},
        weather={"weather_str": "晴", "weather_code": 0},
        battery_pct=90,
        screen_w=400,
        screen_h=300,
        colors=4,
    )
    assert img.size == (400, 300)
    assert content["qr_content"] == "https://inksight.local/test"
    assert content["title"] == "测试二维码"
