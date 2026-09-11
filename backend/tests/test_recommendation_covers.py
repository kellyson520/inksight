"""Tests for Iwara, Qidian, and Pixiv cover generation and recommendation rendering."""
from __future__ import annotations

import asyncio
from unittest.mock import patch, MagicMock
from PIL import Image
import pytest

from core.recommendation_provider import normalize_recommendation_item
from core.providers.iwara_video_provider import _parse_iwara_items, generate_iwara_video
from core.providers.qidian_novel_provider import _parse_qidian_items, generate_qidian_novel
from core.providers.pixiv_daily_provider import generate_pixiv_daily
from core.blocks.context import RenderContext
from core.blocks.recommendation import render_recommendation


def test_normalize_recommendation_item_preserves_image_data():
    """测试 normalize_recommendation_item 不丢弃本地 PIL 兜底图像。"""
    img = Image.new("RGB", (100, 100), (200, 200, 200))
    item = normalize_recommendation_item({
        "title": "测试",
        "image_data": img,
        "cover_url": "https://example.com/cover.jpg",
    }, source="test")
    assert item["image_data"] is img
    assert item["cover_url"] == "https://example.com/cover.jpg"


def test_iwara_parse_items_extracts_full_thumbnail_url():
    """测试 Iwara API 返回的 file_id 和 thumbnail 索引能被正确拼装为完整的 CDN 缩略图 URL。"""
    payload = {
        "results": [
            {
                "id": "vid_123",
                "title": "测试MMD动画",
                "thumbnail": 2,
                "file": {
                    "id": "file_abc_789",
                    "name": "test.mp4",
                },
                "user": {
                    "name": "创作者",
                    "username": "creator",
                },
            }
        ]
    }
    items = _parse_iwara_items(payload)
    assert len(items) == 1
    first = items[0]
    assert first["title"] == "测试MMD动画"
    assert "file_abc_789" in first["cover_url"]
    assert "thumbnail-02.jpg" in first["cover_url"]
    assert first["cover_url"].startswith("https://files.iwara.tv/image/")


def test_qidian_parse_items_from_html_page_data():
    """测试起点提供者能够正确解析移动端 rank 页面数据并生成封面。"""
    html_sample = """
    <html><body>
    <script>
    {"pageContext":{"pageProps":{"pageData":{"hotRank":[
        {"bName":"诡秘之主","bAuth":"爱潜水的乌贼","cat":"玄幻","bid":"1010868264","desc":"简介"}
    ]}}}}
    </script>
    </body></html>
    """
    items = _parse_qidian_items(html_sample)
    assert len(items) == 1
    first = items[0]
    assert first["title"] == "诡秘之主"
    assert "1010868264" in first["cover_url"]
    assert first["cover_url"].startswith("https://bookcover.yuewen.com/")


@pytest.mark.asyncio
async def test_all_recommendation_providers_have_non_empty_covers_on_fallback():
    """确保在无网络或未抓到外网数据时，Iwara、起点、Pixiv 兜底数据均包含有效封面或 image_data。"""
    # 1. Iwara
    with patch("core.outbound_http.outbound_http.get_json", side_effect=RuntimeError("offline")):
        iwara_res = await generate_iwara_video({}, {}, {}, config={})
        iwara_items = iwara_res.get("items", [])
        assert len(iwara_items) > 0
        assert iwara_items[0].get("cover_url") or iwara_items[0].get("image_data"), "Iwara 兜底缺少封面"

    # 2. Qidian
    with patch("core.outbound_http.outbound_http.get_text", side_effect=RuntimeError("offline")):
        qidian_res = await generate_qidian_novel({}, {}, {}, config={})
        qidian_items = qidian_res.get("items", [])
        assert len(qidian_items) > 0
        assert qidian_items[0].get("cover_url") or qidian_items[0].get("image_data"), "Qidian 兜底缺少封面"

    # 3. Pixiv
    with patch("core.outbound_http.outbound_http.get_json", side_effect=RuntimeError("offline")):
        pixiv_res = await generate_pixiv_daily({}, {}, {}, config={})
        pixiv_items = pixiv_res.get("items", [])
        assert len(pixiv_items) > 0
        assert pixiv_items[0].get("cover_url") or pixiv_items[0].get("image_data"), "Pixiv 兜底缺少封面"


def test_recommendation_cover_card_renders_sufficient_height_without_explicit_block_param():
    """测试 recommendation 在 cover_card 模式下，即便 JSON 中未显式指定 card_height，也能动态计算合适卡片高度。"""
    img = Image.new("1", (400, 300), 1)
    from PIL import ImageDraw
    draw = ImageDraw.Draw(img)
    local_cover = Image.new("RGB", (200, 200), (100, 100, 100))
    content = {
        "layout_style": "cover_card",
        "items": [{
            "title": "测试小说",
            "subtitle": "作者",
            "image_data": local_cover,
            "rank_label": "NO.1",
        }],
    }
    ctx = RenderContext(draw=draw, img=img, content=content, screen_w=400, screen_h=300, y=30, footer_height=24)
    # block 未传入 card_height
    render_recommendation(ctx, {"type": "recommendation", "field": "items", "style_field": "layout_style"})
    # 渲染后 ctx.y 必须推进超过 100px（而不是微不足道的 18px）
    assert ctx.y - 30 >= 100, f"Card height too small: {ctx.y - 30}px"
