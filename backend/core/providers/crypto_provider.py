"""
加密货币与全球股票资产行情 Provider (Crypto & Stock Ticker)
下沉委托至核心基础设施 MarketService，保持架构清晰、无冗余代码与统一缓存熔断。
"""
from __future__ import annotations

import logging
from typing import Any

from core.market_service import market_service
from .base import register_provider

logger = logging.getLogger(__name__)


@register_provider("crypto")
async def generate_crypto(
    mode_def: dict[str, Any],
    content_cfg: dict[str, Any],
    fallback: dict[str, Any],
    **kwargs: Any,
) -> dict[str, Any]:
    config = kwargs.get("config") or {}
    mode_settings = config.get("mode_settings") or {}
    mode_overrides = config.get("mode_overrides") or {}
    override = mode_overrides.get("CRYPTO") or {}

    symbol = "BTC"
    if isinstance(override, dict) and override.get("symbol"):
        symbol = str(override["symbol"])
    elif isinstance(mode_settings, dict) and mode_settings.get("symbol"):
        symbol = str(mode_settings["symbol"])
    elif content_cfg.get("symbol"):
        symbol = str(content_cfg["symbol"])

    # 统一通过下沉的 market_service 基础设施拉取 100% 真实行情与分时时序
    try:
        data = await market_service.get_market_data(symbol)
        if data:
            return data
    except Exception as exc:
        logger.warning("[CryptoProvider] Failed to get market data for %s: %s", symbol, exc)

    # 极端异常兜底
    clean_sym = market_service.normalize_symbol(symbol)
    fb = market_service._persisted.get(clean_sym) or fallback
    res = dict(fb)
    return res
