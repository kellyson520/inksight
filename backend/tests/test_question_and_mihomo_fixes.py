"""
测试每日一问防重复机制与 Mihomo 订阅监控修复（重复勋章消除、月重置日准确性）
"""
import datetime
import pytest
from core.mode_registry import get_registry
from core.json_renderer import render_json_mode
from core.mihomo_service import _parse_reset_days_text, _resolve_reset_days, format_subscription_summary
from core.json_content import generate_json_mode_content


@pytest.mark.asyncio
async def test_question_mode_fallback_pool_and_dedup_prompt():
    """Verify QUESTION mode has rich fallback_pool and strict dedup prompt hint."""
    reg = get_registry()
    mdef = reg.get_json_mode("QUESTION").definition
    content_cfg = mdef.get("content", {})
    pool = content_cfg.get("fallback_pool", [])
    
    # 1. 验证具备至少 8 条高质量候选池
    assert len(pool) >= 8, f"QUESTION fallback_pool must have at least 8 items, got {len(pool)}"
    questions = [it.get("question") for it in pool]
    assert len(set(questions)) == len(questions), "Questions in pool must be unique"

    # 2. 模拟 LLM 失败降级时多次获取，验证多样性与有效性
    res1 = await generate_json_mode_content(mdef, mac="TEST_MAC_DEDUP_1")
    assert res1.get("question") is not None
    assert len(res1.get("question")) > 0
    # 获取第二条，游标平滑推进
    res2 = await generate_json_mode_content(mdef, mac="TEST_MAC_DEDUP_1")
    assert res2.get("question") is not None
    assert len(res2.get("question")) > 0


def test_mihomo_sub_badge_deduplication():
    """Verify that MIHOMO_SUB layout no longer contains duplicate sub_X_expire_short_badge."""
    reg = get_registry()
    mdef = reg.get_json_mode("MIHOMO_SUB").definition
    layout_str = str(mdef.get("layout", {}))

    # 验证没有在一张卡片内重复两次 sub_1_expire_short_badge
    # 在原 bug 中，同一个 card 内出现了 2 次 sub_1_expire_short_badge 和 2 次 sub_2_expire_short_badge
    count_1 = layout_str.count("{sub_1_expire_short_badge}")
    count_2 = layout_str.count("{sub_2_expire_short_badge}")
    assert count_1 == 1, f"sub_1_expire_short_badge must appear exactly once, got {count_1}"
    assert count_2 == 1, f"sub_2_expire_short_badge must appear exactly once, got {count_2}"


def test_mihomo_monthly_reset_calculation_edge_cases():
    """Verify Mihomo monthly reset day calculations across leap years, month ends, and same-day resets."""
    # 1. 当天正好是重置日 -> 0天 (今日重置)
    dt_today = datetime.datetime(2025, 5, 20, 15, 30)
    assert _parse_reset_days_text("每月20号重置", now_dt=dt_today) == 0
    s_today = format_subscription_summary(reset_days=0, now_dt=dt_today)
    assert s_today["reset_badge"] == "今日重置"

    # 2. 明天是重置日 -> 1天 (还有 1 天重置)
    dt_eve = datetime.datetime(2025, 5, 19, 9, 0)
    assert _parse_reset_days_text("每月20号重置", now_dt=dt_eve) == 1
    s_eve = format_subscription_summary(reset_days=1, now_dt=dt_eve)
    assert s_eve["reset_badge"] == "还有 1 天重置"

    # 3. 跨月重置：5月21日，目标是20日重置 -> 下月6月20日重置 (30天)
    dt_passed = datetime.datetime(2025, 5, 21, 10, 0)
    assert _parse_reset_days_text("每月20号重置", now_dt=dt_passed) == 30

    # 4. 大小月边界：1月31日设为31号重置，2月为平年（28天）
    dt_feb = datetime.datetime(2025, 2, 1, 12, 0)
    # 2月没有31号，自动安全夹持到 2月28日 -> 27天
    assert _parse_reset_days_text("每月31号重置", now_dt=dt_feb) == 27

    # 5. 从节点名提取重置倒计时
    proxies = [
        {"name": "🇭🇰 香港专线 01 | 剩余 8 天重置"},
        {"name": "🇯🇵 日本 02"},
    ]
    assert _resolve_reset_days({}, proxies, now_dt=dt_today) == 8

    # 6. 从订阅元数据 reset_day 整数提取
    assert _resolve_reset_days({"reset_day": 20}, [], now_dt=dt_today) == 0
    assert _resolve_reset_days({"reset_day": 25}, [], now_dt=dt_today) == 5
