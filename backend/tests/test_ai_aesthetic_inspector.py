"""
测试面向 AI 编程的墨水屏美学与排版诊断体系 (AI-Oriented E-Ink Aesthetics & Typographic Evaluation)：
1. 黄金视觉比率量化评分 (Golden Ratio & Harmony Score)
2. 留白与墨水负荷平衡度 (Ink Density & Breathing Room)
3. 结构化 AI 提示增强 (Structured AI-Ready Feedback with JSON & Markdown)
4. 自适应美学自愈指导建议 (Heuristic Recommendations for LLMs)
"""
from core.layout_inspector import evaluate_eink_aesthetics, inspect_layout, format_ai_dialogue


def test_evaluate_eink_aesthetics_balanced_layout():
    mode_def = {
        "mode_id": "TEST_BEAUTY",
        "layout": {
            "body": [
                {"type": "centered_text", "field": "quote", "font_size": 18, "line_spacing": 8}
            ]
        }
    }
    content = {
        "quote": "博观而约取，厚积而薄发。"
    }

    session = inspect_layout(mode_def, content, screen_w=400, screen_h=300)
    score_report = evaluate_eink_aesthetics(session)

    assert "overall_score" in score_report
    assert 0.0 <= score_report["overall_score"] <= 100.0
    assert "visual_balance" in score_report
    assert "typography_elegance" in score_report
    assert "actionable_advice_for_ai" in score_report


def test_format_ai_dialogue_contains_aesthetic_score():
    mode_def = {
        "mode_id": "TEST_AESTHETIC_REPORT",
        "layout": {
            "body": [
                {"type": "text", "field": "headline", "font_size": 16, "align": "center"}
            ]
        }
    }
    content = {"headline": "人生天地之间，若白驹过隙，忽然而已。"}

    session = inspect_layout(mode_def, content, screen_w=400, screen_h=300)
    report = format_ai_dialogue(session)

    # 验证报告中包含美学综合评分与 AI 视觉理解维度
    assert "美学与和谐度评分" in report or "Aesthetic" in report
    assert "视觉重心" in report or "平衡" in report


def test_evaluate_eink_aesthetics_hierarchy_detection():
    # 测试标题与正文字号过近的扁平层级检测
    mode_def = {
        "mode_id": "TEST_HIERARCHY",
        "layout": {
            "body": [
                {"type": "text", "field": "title", "font_size": 15},
                {"type": "text", "field": "subtitle", "font_size": 14},
                {"type": "text", "field": "body", "font_size": 14},
            ]
        }
    }
    content = {
        "title": "晨间微思",
        "subtitle": "今日专注要务",
        "body": "生活是一场持续的自我超越，保持专注与内心的平静。",
    }
    session = inspect_layout(mode_def, content, screen_w=400, screen_h=300)
    report = evaluate_eink_aesthetics(session)
    assert "hierarchy_ratio" in report
    assert report["hierarchy_ratio"] < 1.15
    assert report["hierarchy_desc"] == "层级偏平"
    assert any("信息层级" in adv for adv in report["actionable_advice_for_ai"])
