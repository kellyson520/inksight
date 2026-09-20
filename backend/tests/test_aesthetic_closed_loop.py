"""
测试 LLM 闭环生成阶段的美学自愈与沉淀驱动 (Aesthetics-Driven Self-Healing & Preload Enrichment):
1. 当大模型生成的内容留白严重过高 (sparse, <30%) 时，智能注入美学扩充反馈
2. 优质且高美学评分 (overall_score >= 85) 的生成内容自动赋予更高质量沉淀分
"""
from core.layout_inspector import evaluate_eink_aesthetics, inspect_layout
import pytest


def test_sparse_layout_triggers_aesthetic_warning():
    mode_def = {
        "mode_id": "TEST_SPARSE",
        "layout": {
            "body": [
                {"type": "text", "field": "text", "font_size": 12, "max_lines": 1}
            ]
        }
    }
    content = {"text": "短。"}

    session = inspect_layout(mode_def, content, screen_w=400, screen_h=300)
    aesthetics = evaluate_eink_aesthetics(session)

    assert session.density_assessment == "sparse"
    assert aesthetics["overall_score"] < 90
    assert any("稀疏" in adv or "空" in adv for adv in aesthetics["actionable_advice_for_ai"])
