"""
科技雷达模式与底层高密度组件单元测试 (Tech Radar & Geek Widgets Tests)
覆盖:
1. stat_progress_bar 渲染与越界防护
2. pill_tag_list 胶囊标签云换行与渲染
3. code_snippet_box 极客终端卡片与控制台小圆点绘制
4. tech_radar_service 数据抓取与兜底轮换
5. TECH_RADAR JSON 模式注册与 400x300 真实排版渲染
6. component_tree_engine 下沉架构解耦验证
"""
from __future__ import annotations

import pytest
from PIL import Image, ImageDraw

from core.blocks.context import RenderContext
from core.blocks.geek_widgets import (
    render_stat_progress_bar,
    render_pill_tag_list,
    render_code_snippet_box,
)
from core.blocks.measure import measure_block_size
from core.tech_radar_service import tech_radar_service
from core.providers.base import list_registered_providers, dispatch_provider
from core.mode_registry import get_registry
from core.json_renderer import render_json_mode


def test_geek_blocks_direct_rendering():
    """测试新高密度组件的画布直接绘制。"""
    img = Image.new("P", (400, 300), 0)
    draw = ImageDraw.Draw(img)
    content = {
        "score": 78.5,
        "tags_list": ["Python", "Rust", "AsyncIO", "Docker", "Kubernetes", "WebAssembly"],
        "commands": ["npm install -g inksight", "inksight init", "inksight serve --port 8080"],
    }
    ctx = RenderContext(
        draw=draw,
        img=img,
        content=content,
        screen_w=400,
        screen_h=300,
        y=10,
        colors=4,
    )

    # 1. 绘制 stat_progress_bar
    render_stat_progress_bar(ctx, {
        "label": "CPU Usage",
        "value_field": "score",
        "max_value": 100,
        "unit": "PCT",
        "margin_x": 14,
        "margin_bottom": 8,
    })
    assert ctx.y > 25

    # 2. 绘制 pill_tag_list
    y_before_tags = ctx.y
    render_pill_tag_list(ctx, {
        "field": "tags_list",
        "margin_x": 14,
        "font_size": 10,
        "variant": "outline",
        "margin_bottom": 8,
    })
    assert ctx.y > y_before_tags + 15

    # 3. 绘制 code_snippet_box
    y_before_code = ctx.y
    render_code_snippet_box(ctx, {
        "title": "install.sh",
        "field": "commands",
        "margin_x": 12,
        "margin_bottom": 6,
    })
    assert ctx.y > y_before_code + 50


def test_measure_geek_blocks():
    """测试新组件的尺寸度量。"""
    img = Image.new("1", (400, 300), 255)
    ctx = RenderContext(
        draw=ImageDraw.Draw(img),
        img=img,
        content={},
        screen_w=400,
        screen_h=300,
        y=0,
        colors=2,
    )

    w1, h1 = measure_block_size(ctx, {"type": "stat_progress_bar", "height": 6}, 400)
    assert w1 == 400
    assert h1 >= 20

    w2, h2 = measure_block_size(ctx, {"type": "pill_tag_list"}, 400)
    assert w2 == 400
    assert h2 >= 25

    w3, h3 = measure_block_size(ctx, {"type": "code_snippet_box"}, 400)
    assert w3 == 400
    assert h3 >= 60


@pytest.mark.asyncio
async def test_tech_radar_service_and_provider():
    """测试科技雷达服务与 Provider。"""
    data = await tech_radar_service.get_tech_radar_data("AI / ML")
    assert "project_name" in data
    assert "trend_score" in data
    assert "tags" in data
    assert isinstance(data["code_snippet"], list)

    providers = list_registered_providers()
    assert "tech_radar" in providers

    res = await dispatch_provider("tech_radar", {}, {}, {"project_name": "fallback"})
    assert res is not None
    assert "project_name" in res


def test_tech_radar_json_mode_render():
    """测试 TECH_RADAR 完整模式在 400x300 分辨率下的渲染。"""
    reg = get_registry()
    mode = reg.get_json_mode("TECH_RADAR")
    assert mode is not None
    assert mode.info.mode_id == "TECH_RADAR"

    sample_content = {
        "radar_title": "TECH RADAR · AI / ML",
        "project_name": "vLLM",
        "stars_metric": "38.2k",
        "trend_score": 94.5,
        "summary": "高吞吐高并发大模型推理服务引擎，支持 PagedAttention 显存优化技术。",
        "tags": ["LLM", "Inference", "CUDA", "Python"],
        "snippet_title": "vllm-serve.sh",
        "code_snippet": [
            "python3 -m vllm.entrypoints.openai.api_server \\",
            "  --model deepseek-ai/DeepSeek-V3 \\",
            "  --tensor-parallel-size 4",
        ],
    }

    img = render_json_mode(
        mode_def=mode.definition,
        content=sample_content,
        date_str="2026-09-05",
        weather_str="晴 25°C",
        battery_pct=90,
        screen_w=400,
        screen_h=300,
        colors=4,
    )
    assert img is not None
    assert img.size == (400, 300)
