"""Tests for Douban movie rotation and Qidian novel left-text right-image card layout."""
from __future__ import annotations

import asyncio
from unittest.mock import patch
from PIL import Image, ImageDraw
import pytest

from core.providers.douban_movie_provider import generate_douban_movie
from core.blocks.context import RenderContext
from core.blocks.recommendation import render_recommendation


@pytest.mark.asyncio
async def test_douban_movie_rotates_across_refreshes_or_cycles():
    """测试豆瓣电影在多次请求或不同刷新周期/时间/种子下能够轮换推荐不同电影，而不是固定为同一部。"""
    # 模拟不同的调用周期/序号或者时间点
    mac = "70:AF:09:75:51:84"
    titles = set()
    for cycle in range(5):
        # 模拟设备不同周期或时间点刷新
        date_ctx = {"date_str": "9月11日 周五", "time_str": f"12:{cycle:02d}:00"}
        res = await generate_douban_movie(
            {},
            {"category": "ALL"},
            {},
            config={},
            mac=mac,
            device_mac=mac,
            cycle_index=cycle,
            date_ctx=date_ctx,
        )
        assert res.get("title"), "豆瓣电影必须返回有效电影标题"
        titles.add(res["title"])

    # 5 次不同 cycle/时间的调用中，必须出现至少 2 部以上不同电影，证明不会死锁在固定一部
    assert len(titles) >= 2, f"Douban movie did not rotate! titles={titles}"


def test_recommendation_card_renders_left_text_right_image_layout():
    """测试 recommendation 在 cover_card 模式下，支持左边书名/简介、右边图片的横向排版。"""
    screen_w, screen_h = 400, 300
    img = Image.new("1", (screen_w, screen_h), 1)
    draw = ImageDraw.Draw(img)

    cover = Image.new("RGB", (100, 140), (80, 80, 80))
    content = {
        "layout_style": "cover_card",
        "items": [{
            "title": "诡秘之主",
            "subtitle": "爱潜水的乌贼 · 异世大陆",
            "description": "蒸汽与机械的浪潮中，谁能触及非凡？历史和黑暗的迷雾里，又是谁在耳语？",
            "image_data": cover,
            "rank_label": "NO.1",
        }],
    }
    ctx = RenderContext(draw=draw, img=img, content=content, screen_w=screen_w, screen_h=screen_h, y=30, footer_height=24)

    # 声明 card_layout 为 "left_text_right_image"
    render_recommendation(ctx, {
        "type": "recommendation",
        "field": "items",
        "style_field": "layout_style",
        "card_layout": "left_text_right_image",
    })

    # 验证渲染完成，ctx.y 推进
    assert ctx.y > 100, f"Card height too small: {ctx.y}"
    # 验证右侧区域（x 在 260~380 之间，y 在 40~200 之间）绘制了封面像素（非白像素存在）
    right_pixels = [img.getpixel((x, y)) for y in range(40, 200) for x in range(280, 380)]
    non_white_right = sum(1 for p in right_pixels if p == 0)
    assert non_white_right > 50, "Right area did not render cover image!"
