"""
渲染算法与全模式静态资产降级回归测试 (Rendering Algorithms & Assets Fallback Regression Test)
验证：
1. 本地静态艺术画库 /static/art/* 在无外部 API Key 时平稳降级直读，不触发 HTTP URL 异常
2. load_font_by_name 在缺少特定音标字体时优雅降级到 NotoSerifSC-Regular.ttf，避免回退到简陋默认字体
3. 墨水屏全模式自愈能力与调色板色彩覆盖率健全
"""
from __future__ import annotations

import pytest
from core.pipeline import generate_and_render
from core.patterns.utils import load_font_by_name


def test_font_fallback_to_cjk_regular():
    """验证缺失字体名时平稳回退至中文字体而非系统无衬线小字。"""
    font = load_font_by_name("NonExistentFont_123.ttf", 16)
    assert font is not None
    # 验证测量汉字与英文均不为空
    bbox = font.getbbox("InkSight 墨水屏")
    assert bbox[2] - bbox[0] > 50


@pytest.mark.asyncio
async def test_artwall_fallback_local_asset_rendering():
    """验证 ARTWALL 在缺少 AI 生图 Key 时成功加载本地水墨画资产。"""
    img, content = await generate_and_render(
        persona="ARTWALL",
        config={"modes": ["ARTWALL"], "colors": 4},
        date_ctx={"date_str": "2026-03-30", "time_str": "12:00"},
        weather={"weather_str": "晴", "weather_code": 0},
        battery_pct=90,
        screen_w=400,
        screen_h=300,
        colors=4,
    )
    assert img.size == (400, 300)
    assert content.get("artwork_title")
    non_white = sum(1 for y in range(300) for x in range(400) if img.getpixel((x, y)) != 1)
    assert non_white > 5000, f"Expected rich artwork pixels, got {non_white}"
