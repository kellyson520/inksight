"""
二维码展示模式与原生渲染 Block 单元测试 (QR Code Mode & Block Tests)
"""
from __future__ import annotations

import pytest
from PIL import Image, ImageDraw

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
