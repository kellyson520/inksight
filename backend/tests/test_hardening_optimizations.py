"""Tests for image transparency, mihomo subscription, and small-screen recommendation hardening."""
from __future__ import annotations

import datetime
from PIL import Image, ImageDraw
import pytest

from core.image_processing import quantize_image_for_eink
from core.mihomo_service import _parse_reset_days_text, format_subscription_summary
from core.blocks.context import RenderContext
from core.blocks.recommendation import render_recommendation


def test_quantize_image_transparent_rgba_composited_on_white():
    """透明 RGBA 图片转 e-ink 时，透明区域必须合成在白底上，而非变成黑色。"""
    # 创建一个完全透明的图像，中心有一个纯黑圆
    rgba = Image.new("RGBA", (100, 100), (0, 0, 0, 0))
    draw = ImageDraw.Draw(rgba)
    draw.rectangle([40, 40, 60, 60], fill=(0, 0, 0, 255))

    # 量化到 2 色 (B/W)
    out_bw = quantize_image_for_eink(rgba, colors=2)
    # 检查四周本是透明的像素 (0, 0)，在 2 色下必须为白 (非 0，PIL mode 1 下为 255 或 1)
    assert out_bw.getpixel((0, 0)) in (1, 255), "Transparent pixel turned black in BW mode!"
    # 检查中心黑色像素必须为黑 (0)
    assert out_bw.getpixel((50, 50)) == 0, "Center black pixel was lost!"

    # 量化到 4 色 (B/W/R/Y)
    out_4c = quantize_image_for_eink(rgba, colors=4)
    # 4 色调色板下白色为 1
    assert out_4c.getpixel((0, 0)) == 1, "Transparent pixel turned non-white in 4-color mode!"


def test_mihomo_parse_reset_days_text_various_formats():
    """测试重置天数解析支持多种常见机场重置描述。"""
    # 格式 1: 还有 X 天
    assert _parse_reset_days_text("本周期还有 5 天重置") == 5
    # 格式 2: reset in X days
    assert _parse_reset_days_text("Data reset in 12 days") == 12
    # 格式 3: 每月 X 日重置（动态计算距离该日的剩余天数）
    now = datetime.datetime.now()
    # 如果下个重置日在未来 3 天
    target_day = (now + datetime.timedelta(days=3)).day
    text = f"每月 {target_day} 日重置"
    assert _parse_reset_days_text(text) == 3


def test_mihomo_format_subscription_summary_handles_ms_timestamp():
    """测试 format_subscription_summary 能正确处理毫秒级 (13位) 时间戳。"""
    # 距离当前时间 90 天后的毫秒级时间戳
    now = datetime.datetime.now()
    future_ms = int((now.timestamp() + 86400 * 90) * 1000)
    summary = format_subscription_summary(
        upload_bytes=1024,
        download_bytes=2048,
        total_bytes=100 * 1024 * 1024 * 1024,
        expire_timestamp=future_ms,
        reset_days=10,
    )
    assert "剩余" in summary["days_badge"]
    assert "已过期" not in summary["days_badge"]


def test_recommendation_cover_card_small_screen_bounds():
    """在 296x128 小屏分辨率下，cover_card 渲染不能超出屏幕底部（保留 footer 空间）。"""
    screen_w, screen_h = 296, 128
    footer_h = 20
    img = Image.new("1", (screen_w, screen_h), 1)
    draw = ImageDraw.Draw(img)
    content = {
        "layout_style": "cover_card",
        "items": [{
            "title": "测试小说超长标题超出屏幕宽度测试自动截断与排版保护",
            "subtitle": "作者 · 玄幻",
            "rank_label": "NO.1",
        }],
    }
    ctx = RenderContext(draw=draw, img=img, content=content, screen_w=screen_w, screen_h=screen_h, y=24, footer_height=footer_h)
    render_recommendation(ctx, {"type": "recommendation", "field": "items", "style_field": "layout_style"})

    # 渲染后 ctx.y 不能侵入 footer 区域 (screen_h - footer_h)
    assert ctx.y <= screen_h - footer_h + 2, f"ctx.y ({ctx.y}) penetrated footer ({screen_h - footer_h})"
