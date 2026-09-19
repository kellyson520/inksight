"""
测试墨水屏布局空间反思引擎 (Layout Inspector & AI-readable Session)
"""
import pytest
from core.layout_inspector import inspect_layout, format_ascii_preview, format_ai_dialogue, LayoutSession


def test_inspect_layout_basic_mode():
    mode_def = {
        "mode_id": "TEST_QUOTE",
        "display_name": "每日金句",
        "layout": {
            "status_bar": {"line_width": 1},
            "body": [
                {
                    "type": "centered_text",
                    "template": "生活不是等待风暴过去",
                    "font_size": 20,
                    "margin_bottom": 10,
                },
                {
                    "type": "text",
                    "template": "而是在风雨中学会跳舞。这是一段稍长的测试正文，用于验证分行和测量效果。",
                    "font_size": 14,
                    "line_height": 22,
                },
            ],
            "footer": {"label": "测试模式", "height": 30},
        },
    }
    content = {}

    session = inspect_layout(mode_def, content, screen_w=400, screen_h=300)

    assert isinstance(session, LayoutSession)
    assert session.screen_w == 400
    assert session.screen_h == 300
    assert session.status_bar_h > 0
    assert session.footer_h > 0
    assert len(session.blocks) == 2

    # 检查第一个 block
    b1 = session.blocks[0]
    assert b1.block_type == "centered_text"
    assert b1.height > 0
    assert "生活不是等待风暴过去" in b1.text_preview

    # 检查第二个 block
    b2 = session.blocks[1]
    assert b2.block_type == "text"
    assert len(b2.rendered_lines) >= 1
    assert b2.y >= b1.y + b1.height

    # 检查剩余空间预算
    assert session.remaining_height_px > 0
    assert session.has_truncation is False


def test_inspect_layout_detects_overflow_and_truncation():
    mode_def = {
        "mode_id": "TEST_OVERFLOW",
        "layout": {
            "body": [
                {
                    "type": "text",
                    "template": "超长文本 " * 150,  # 故意构造超长文本导致超出屏幕
                    "font_size": 16,
                    "line_height": 24,
                }
            ],
        },
    }
    session = inspect_layout(mode_def, {}, screen_w=400, screen_h=300)
    assert session.has_truncation is True
    assert session.density_assessment == "crowded"
    assert len(session.warnings) > 0


def test_format_ascii_preview():
    mode_def = {
        "mode_id": "TEST_ASCII",
        "layout": {
            "body": [
                {"type": "centered_text", "template": "标题测试", "font_size": 18},
                {"type": "separator"},
                {"type": "text", "template": "正文第一行\n正文第二行", "font_size": 14},
            ],
        },
    }
    session = inspect_layout(mode_def, {}, screen_w=400, screen_h=300)
    ascii_art = format_ascii_preview(session, cols=36, rows=14)

    assert "[StatusBar]" in ascii_art
    assert "Footer" in ascii_art
    assert "+" in ascii_art and "|" in ascii_art


def test_format_ai_dialogue():
    mode_def = {
        "mode_id": "TEST_AI",
        "layout": {
            "body": [
                {"type": "text", "template": "测试内容", "font_size": 14},
            ],
        },
    }
    session = inspect_layout(mode_def, {}, screen_w=400, screen_h=300)
    dialogue = format_ai_dialogue(session)

from PIL import Image
from core.json_renderer import render_json_mode


def test_render_json_mode_with_return_session():
    mode_def = {
        "mode_id": "TEST_RENDER_SESSION",
        "display_name": "测试会话",
        "layout": {
            "body": [
                {"type": "centered_text", "template": "墨水屏真实渲染", "font_size": 18},
                {"type": "text", "template": "这是伴随渲染返回的排版会话诊断", "font_size": 14},
            ],
        },
    }
    content = {}

    # 1. 默认调用：只返回 PIL Image
    img = render_json_mode(mode_def, content, date_str="5月18日", weather_str="25°C", battery_pct=85.0)
    assert isinstance(img, Image.Image)

    # 2. 携带 return_session=True：返回 (img, session)
from unittest.mock import AsyncMock, patch
from core.json_content import generate_json_mode_content


@pytest.mark.asyncio
async def test_json_content_layout_inspection_and_healing():
    mode_def = {
        "mode_id": "TEST_TRIM",
        "display_name": "修剪测试",
        "content": {
            "type": "llm",
            "prompt_template": "生成格言",
            "fallback": {"text": "兜底"},
        },
        "layout": {
            "body": [
                {"type": "text", "field": "text", "font_size": 16, "line_height": 24},
            ],
        },
    }

    # 模拟超长文本，字数足够多，确保在 296x128 小屏幕上必然发生截断
    overlong_text = (
        "这是第一句非常优美的话语。这是第二句深刻的见解。"
        "这是第三句由于字数太多无法在小屏幕完整显示的被截断文字片段。"
        "这是第四句多余的内容肯定会被挤出屏幕外的文字片段"
    )

    with (
        patch("core.json_content._call_llm", new_callable=AsyncMock, return_value=overlong_text),
        patch("core.json_content._call_llm_resilient", new_callable=AsyncMock, return_value=overlong_text),
        patch("core.json_content.DEDUP_MAX_RETRIES", 0),  # 强制 0 次重试以触发兜底标点修剪保护
    ):
        result = await generate_json_mode_content(
            mode_def,
            date_str="5月18日",
            weather_str="晴",
            screen_w=296,
            screen_h=128,
        )

import httpx
from api.index import app


@pytest.mark.asyncio
async def test_api_mode_layout_session():
    """测试 /api/modes/{mode_id}/layout-session 路由返回结构化会话与 AI 对话报告。"""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # 1. 默认 JSON 格式
        resp = await client.get("/api/modes/DAILY/layout-session?w=400&h=300")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert data["session"]["mode_id"] == "DAILY"
        assert data["session"]["screen"] == "400x300"
        assert "fill_ratio_percent" in data["session"]

        # 2. Markdown / 对话格式 (供 AI Agent 直接消费)
        resp_text = await client.get("/api/modes/DAILY/layout-session?w=400&h=300&format=dialogue")
        assert resp_text.status_code == 200
        text_content = resp_text.text
        assert "### 墨水屏物理版面诊断报告" in text_content
        assert "版面拓扑预览" in text_content



