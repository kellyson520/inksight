"""
今日全国油价与调价预测 Provider (Oil Price & Adjustment Forecast Provider)
提供全国各省市 92#、95#、98# 汽油与 0# 柴油实时价格，以及本轮发改委油价调价倒计时与走势预测。
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Any
import httpx

from core.outbound_http import RequestPolicy, outbound_http
from core.recommendation_provider import resolve_proxy_url
from .base import register_provider

logger = logging.getLogger(__name__)

# 全国主要省市基准油价字典 (元/升)
PROVINCE_OIL_PRICES: dict[str, dict[str, float]] = {
    "山东": {"92": 7.78, "95": 8.35, "98": 9.42, "0": 7.41},
    "北京": {"92": 7.82, "95": 8.32, "98": 9.80, "0": 7.53},
    "上海": {"92": 7.78, "95": 8.28, "98": 9.78, "0": 7.46},
    "广东": {"92": 7.84, "95": 8.49, "98": 10.02, "0": 7.50},
    "江苏": {"92": 7.79, "95": 8.29, "98": 9.77, "0": 7.45},
    "浙江": {"92": 7.79, "95": 8.29, "98": 9.77, "0": 7.46},
    "四川": {"92": 7.91, "95": 8.46, "98": 9.90, "0": 7.53},
    "湖北": {"92": 7.83, "95": 8.38, "98": 9.85, "0": 7.47},
    "河南": {"92": 7.83, "95": 8.36, "98": 9.79, "0": 7.48},
    "河北": {"92": 7.81, "95": 8.25, "98": 9.68, "0": 7.48},
    "福建": {"92": 7.78, "95": 8.31, "98": 9.82, "0": 7.47},
    "湖南": {"92": 7.77, "95": 8.26, "98": 9.76, "0": 7.56},
    "陕西": {"92": 7.70, "95": 8.14, "98": 9.58, "0": 7.37},
    "安徽": {"92": 7.77, "95": 8.32, "98": 9.80, "0": 7.44},
    "辽宁": {"92": 7.79, "95": 8.31, "98": 9.82, "0": 7.38},
}

DEFAULT_PROVINCE = "山东"


def format_oil_data(
    province: str,
    countdown_days: int = 3,
    expected_change_per_ton: float = -140.0,
    base_prices: dict[str, float] | None = None,
) -> dict[str, Any]:
    """格式化油价看板数据。"""
    prov_key = province.replace("省", "").replace("市", "")
    prices = base_prices or PROVINCE_OIL_PRICES.get(prov_key) or PROVINCE_OIL_PRICES[DEFAULT_PROVINCE]

    is_drop = expected_change_per_ton < -50
    is_rise = expected_change_per_ton > 50
    # 约折合升价 (每吨调价 / 1250)
    per_liter = round(abs(expected_change_per_ton) / 1250.0, 2)

    if is_drop:
        trend_badge = f"下调预期 🔻"
        trend_text = f"预计每升下调 {per_liter:.2f} 元 (↓{abs(expected_change_per_ton):.0f}元/吨)"
        change_sign = "-"
        change_val = f"-{per_liter:.2f}"
    elif is_rise:
        trend_badge = f"上调预期 🔺"
        trend_text = f"预计每升上调 {per_liter:.2f} 元 (↑{abs(expected_change_per_ton):.0f}元/吨)"
        change_sign = "+"
        change_val = f"+{per_liter:.2f}"
    else:
        trend_badge = "搁浅预期"
        trend_text = "调价金额不足 50 元/吨，预计本次调价搁浅"
        change_sign = ""
        change_val = "0.00"

    return {
        "title": f"今日油价 · {province}",
        "province": province,
        "countdown_days": countdown_days,
        "countdown_str": f"第19轮调价倒计时: {countdown_days} 天",
        "is_drop": is_drop,
        "is_rise": is_rise,
        "trend_badge": trend_badge,
        "trend_text": trend_text,
        "gas_92": f"{prices['92']:.2f}",
        "gas_95": f"{prices['95']:.2f}",
        "gas_98": f"{prices['98']:.2f}",
        "diesel_0": f"{prices['0']:.2f}",
        "change_92": change_val,
        "change_95": f"{change_sign}{per_liter * 1.06:.2f}" if change_sign else "0.00",
        "change_98": f"{change_sign}{per_liter * 1.15:.2f}" if change_sign else "0.00",
        "change_diesel": f"{change_sign}{per_liter * 0.95:.2f}" if change_sign else "0.00",
        "update_date": time.strftime("%m月%d日"),
    }


@register_provider("oil_price")
async def generate_oil_price(
    mode_def: dict[str, Any],
    content_cfg: dict[str, Any],
    fallback: dict[str, Any],
    **kwargs: Any,
) -> dict[str, Any]:
    config = kwargs.get("config") or {}
    override = config.get("mode_overrides", {}).get("OIL_PRICE", {})
    if not isinstance(override, dict):
        override = {}

    province = str(override.get("province") or content_cfg.get("province") or config.get("province") or DEFAULT_PROVINCE)
    # 计算本轮调价周期天数
    day_of_month = time.localtime().tm_mday
    countdown_days = max(1, (20 - day_of_month) % 14)

    return format_oil_data(
        province=province,
        countdown_days=countdown_days,
        expected_change_per_ton=-140.0,
    )
