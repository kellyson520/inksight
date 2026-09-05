"""
Unit & Integration tests for new Productivity & Lifestyle Modes:
- TODO_MATRIX (四象限时间管理待办矩阵)
- HABIT_TRACKER (生活健康打卡看板)
- CPA_QUOTA (远程多实例与非本地链接模式)
"""
from __future__ import annotations

import pytest
from core.pipeline import generate_and_render
from core.cpa_keeper_service import CpaKeeperService


@pytest.mark.asyncio
async def test_todo_matrix_mode_zh_and_en():
    """验证四象限待办矩阵模式在中英双语环境下的正确生成与渲染。"""
    for lang, expected_title in [("zh", "今日四象限待办矩阵"), ("en", "Today Eisenhower Matrix")]:
        img, content = await generate_and_render(
            persona="TODO_MATRIX",
            config={"mode_language": lang},
            date_ctx={"time_str": "15:00", "date_str": "09/05"},
            weather={"weather_str": "晴", "weather_code": 0},
            battery_pct=90.0,
            screen_w=400,
            screen_h=300,
            colors=4,
        )
        assert img.size == (400, 300)
        assert content["title"] == expected_title
        assert "q1_title" in content
        assert "q2_title" in content
        assert "q3_title" in content
        assert "q4_title" in content
        assert "progress_pct" in content


@pytest.mark.asyncio
async def test_habit_tracker_mode_zh_and_en():
    """验证生活与健康打卡模式在中英双语环境下的正确生成与渲染。"""
    for lang, expected_title in [("zh", "每日生活与健康打卡"), ("en", "Daily Habit & Health Tracker")]:
        img, content = await generate_and_render(
            persona="HABIT_TRACKER",
            config={"mode_language": lang},
            date_ctx={"time_str": "16:00", "date_str": "09/05"},
            weather={"weather_str": "晴", "weather_code": 0},
            battery_pct=95.0,
            screen_w=400,
            screen_h=300,
            colors=4,
        )
        assert img.size == (400, 300)
        assert content["title"] == expected_title
        assert "water_val" in content
        assert "reading_val" in content
        assert "stand_val" in content
        assert "overall_progress" in content


def test_cpa_keeper_remote_url_support():
    """验证 CpaKeeperService 正确识别与支持非本地远程 CPA 与 Keeper 地址。"""
    service = CpaKeeperService()
    remote_ov = {
        "cpa_url": "https://remote.cpa.cluster.local:8443",
        "keeper_url": "https://remote.keeper.cluster.local:8082",
        "keeper_password": "test-remote-pass",
    }
    health = service.check_health(config_override=remote_ov)
    assert health["cpa_is_remote"] is True
    assert health["keeper_is_remote"] is True

    content_zh = service.get_mode_content(config_override={"view": "auths", **remote_ov}, language="zh")
    assert "title" in content_zh
    assert "header_status" in content_zh

    content_en = service.get_mode_content(config_override={"view": "auths", **remote_ov}, language="en")
    assert "title" in content_en
    assert "header_status" in content_en
