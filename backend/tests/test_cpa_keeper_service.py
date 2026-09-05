"""
Unit tests for CpaKeeperService and CPA Quota Dashboard API & Rendering.
"""
import pytest
from core.cpa_keeper_service import CpaKeeperService, _format_token_count
from core.pipeline import generate_and_render


def test_token_formatting():
    assert _format_token_count(500) == "500"
    assert _format_token_count(1500) == "1.5K"
    assert _format_token_count(65_200_000) == "65.2M"
    assert _format_token_count(3_150_000_000) == "3.15B"


def test_cpa_keeper_health_and_aggregation():
    svc = CpaKeeperService()
    health = svc.check_health()
    assert isinstance(health, dict)
    assert "cpa_online" in health
    assert "keeper_online" in health

    metrics = svc.get_aggregated_metrics(force_refresh=True)
    assert "today_tokens_str" in metrics
    assert "today_requests" in metrics
    assert "today_success_rate" in metrics
    assert "total_cost_str" in metrics
    assert "users" in metrics
    assert "top_models" in metrics
    assert len(metrics["users"]) > 0


def test_cpa_keeper_mode_content():
    svc = CpaKeeperService()
    content_zh = svc.get_mode_content(language="zh")
    assert content_zh["title"] == "CPA 额度仪表盘"
    assert "今日 Token" in content_zh["today_summary"]
    assert "user_1_name" in content_zh

    content_en = svc.get_mode_content(language="en")
    assert content_en["title"] == "CPA Quota Dashboard"
    assert "Today Tokens" in content_en["today_summary"]


@pytest.mark.asyncio
async def test_cpa_quota_pipeline_render():
    img, content = await generate_and_render(
        persona="CPA_QUOTA",
        config={},
        date_ctx={"time_str": "14:00", "date_str": "09/05"},
        weather={"weather_str": "晴", "weather_code": 0},
        battery_pct=95.0,
        screen_w=400,
        screen_h=300,
        colors=4,
    )
    assert img.size == (400, 300)
    assert content is not None
    assert content.get("title") in ("CPA 额度仪表盘", "CPA Quota Dashboard")
