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
    assert "auth_identities" in metrics
    # 验证仅收录运行中的本地认证文件（排除第三方 APIKey，当前为 2 个）
    assert len(metrics["auth_identities"]) == 2
    first_auth = metrics["auth_identities"][0]
    assert "display_name" in first_auth
    assert "reset_5h_str" in first_auth
    assert "reset_7d_str" in first_auth
    assert "tokens_str" in first_auth


def test_cpa_keeper_mode_content_views():
    svc = CpaKeeperService()

    # 1. 认证文件视图 (auths)
    content_auths = svc.get_mode_content(config_override={"view": "auths"}, language="zh")
    assert content_auths["title"] == "本地认证文件与限额看板"
    assert "运行中文件" in content_auths["summary_1_label"]
    assert "5小时窗口重置" in content_auths["summary_2_label"]
    assert "card_1_title" in content_auths
    assert "5h重置" in content_auths["card_1_reset_text"]
    assert "7天重置" in content_auths["card_1_reset_text"]
    assert "card_1_ring_val" in content_auths

    # 2. 综合总览视图 (overview)
    content_overview = svc.get_mode_content(config_override={"view": "overview"}, language="zh")
    assert content_overview["title"] == "CPA 额度综合看板"

    # 3. 用户消费账单视图 (users)
    content_users = svc.get_mode_content(config_override={"view": "users"}, language="zh")
    assert content_users["title"] == "用户与 Key 消费排行榜"

    # 4. 模型消耗视图 (models)
    content_models = svc.get_mode_content(config_override={"view": "models"}, language="zh")
    assert content_models["title"] == "AI 模型消耗与请求分布"


@pytest.mark.asyncio
async def test_cpa_quota_pipeline_render_all_views():
    for view_mode in ["auths", "overview", "users", "models"]:
        img, content = await generate_and_render(
            persona="CPA_QUOTA",
            config={"mode_overrides": {"CPA_QUOTA": {"view": view_mode}}},
            date_ctx={"time_str": "14:00", "date_str": "09/05"},
            weather={"weather_str": "晴", "weather_code": 0},
            battery_pct=95.0,
            screen_w=400,
            screen_h=300,
            colors=4,
        )
        assert img.size == (400, 300)
        assert content is not None
        assert "summary_1_val" in content


@pytest.mark.asyncio
async def test_cpa_keeper_realtime_force_refresh():
    """验证通过 pipeline 获取的内容是当前实时数据而非静态 fallback。"""
    import asyncio
    from core.cpa_keeper_service import cpa_keeper_service

    content_1 = cpa_keeper_service.get_mode_content(force_refresh=True)
    await asyncio.sleep(1.05)
    content_2 = cpa_keeper_service.get_mode_content(force_refresh=True)

    assert content_1["update_time"] != content_2["update_time"]
    assert content_2["update_time"] != "12:00:00"  # 确保不是硬编码的 fallback


def test_quota_color_thresholds():
    """验证额度百分比颜色阈值规则：<20%红色，<=60%黄色，其余黑色。"""
    from core.cpa_keeper_service import _calc_quota_color

    assert _calc_quota_color(0) == "red"
    assert _calc_quota_color(15) == "red"
    assert _calc_quota_color(19.9) == "red"
    assert _calc_quota_color(20) == "yellow"
    assert _calc_quota_color(45) == "yellow"
    assert _calc_quota_color(60) == "yellow"
    assert _calc_quota_color(60.1) == "black"
    assert _calc_quota_color(85) == "black"
    assert _calc_quota_color(100) == "black"


def test_progress_ring_renders_expected_colors():
    """验证环形进度条组件在4色模式下按百分比阈值渲染红/黄/黑。"""
    from PIL import Image, ImageDraw
    from core.blocks.context import RenderContext
    from core.blocks.gauges import render_progress_ring
    from core.config import EINK_4COLOR_PALETTE

    # 1. 测试 < 20% (红色，index 3)
    img_red = Image.new("P", (100, 100), 1)
    img_red.putpalette(EINK_4COLOR_PALETTE)
    ctx_red = RenderContext(draw=ImageDraw.Draw(img_red), img=img_red, content={"pct": 15}, screen_w=100, screen_h=100, colors=4)
    render_progress_ring(ctx_red, {"type": "progress_ring", "field": "pct", "color_by_percent": True, "size": 40})
    red_pixels = [c for c in img_red.getcolors() if c[1] == 3]
    assert len(red_pixels) > 0

    # 2. 测试 <= 60% (黄色，index 2)
    img_yel = Image.new("P", (100, 100), 1)
    img_yel.putpalette(EINK_4COLOR_PALETTE)
    ctx_yel = RenderContext(draw=ImageDraw.Draw(img_yel), img=img_yel, content={"pct": 50}, screen_w=100, screen_h=100, colors=4)
    render_progress_ring(ctx_yel, {"type": "progress_ring", "field": "pct", "color_by_percent": True, "size": 40})
    yellow_pixels = [c for c in img_yel.getcolors() if c[1] == 2]
    assert len(yellow_pixels) > 0

    # 3. 测试 > 60% (黑色，index 0)
    img_blk = Image.new("P", (100, 100), 1)
    img_blk.putpalette(EINK_4COLOR_PALETTE)
    ctx_blk = RenderContext(draw=ImageDraw.Draw(img_blk), img=img_blk, content={"pct": 85}, screen_w=100, screen_h=100, colors=4)
    render_progress_ring(ctx_blk, {"type": "progress_ring", "field": "pct", "color_by_percent": True, "size": 40})
    has_red = any(c[1] == 3 for c in img_blk.getcolors())
    has_yellow = any(c[1] == 2 for c in img_blk.getcolors())
    assert not has_red
    assert not has_yellow

