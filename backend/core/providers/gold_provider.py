"""
黄金行情走势 Provider (Gold Trend Provider)
打通国际伦敦金 (XAU/USD)、国内沪金主力 (AU0) 与上海金交所现货 (Au99.99) 的实时行情与分时走势图。
【规范约束】：严禁 Emoji，支持 24 点分时 sparkline 走势与双源对照。
"""
from __future__ import annotations

import logging
from typing import Any

from core.market_service import market_service
from .base import register_provider

logger = logging.getLogger(__name__)


@register_provider("gold")
async def generate_gold(
    mode_def: dict[str, Any],
    content_cfg: dict[str, Any],
    fallback: dict[str, Any],
    **kwargs: Any,
) -> dict[str, Any]:
    config = kwargs.get("config") or {}
    mode_settings = config.get("mode_settings") or {}
    mode_overrides = config.get("mode_overrides") or {}
    override = mode_overrides.get("GOLD") or {}

    symbol = "AU0"
    if isinstance(override, dict) and override.get("symbol"):
        symbol = str(override["symbol"])
    elif isinstance(mode_settings, dict) and mode_settings.get("symbol"):
        symbol = str(mode_settings["symbol"])
    elif content_cfg.get("symbol"):
        symbol = str(content_cfg["symbol"])

    try:
        data = await market_service.get_gold_data(symbol)
        if data:
            return data
    except Exception as exc:
        logger.warning("[GoldProvider] Failed to get gold data for %s: %s", symbol, exc)

    # 兜底
    res = dict(fallback)
    return res
