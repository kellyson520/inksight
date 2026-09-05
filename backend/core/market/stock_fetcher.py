"""
股票市场行情抓取器 (Stock Market Fetcher)
支持主流美股与自定义标的，结合腾讯实时行情与新浪分时时序数据。
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from typing import Any

from core.http_client import get_async_client
from .crypto_fetcher import downsample

logger = logging.getLogger(__name__)

STOCK_SYMBOLS = {"AAPL", "TSLA", "NVDA", "MSFT", "GOOGL", "AMZN", "META", "BABA"}

STOCK_NAMES: dict[str, str] = {
    "AAPL": "苹果",
    "TSLA": "特斯拉",
    "NVDA": "英伟达",
    "MSFT": "微软",
    "GOOGL": "谷歌",
    "AMZN": "亚马逊",
    "META": "Meta",
    "BABA": "阿里巴巴",
}

SEED_STOCK_DATA: dict[str, dict[str, Any]] = {
    "AAPL": {
        "symbol": "AAPL",
        "name": "苹果 (AAPL)",
        "price": "$234.80",
        "change_24h": "+1.25%",
        "is_up": True,
        "high_24h": "$236.10",
        "low_24h": "$232.50",
        "update_time": "实时分时",
        "sparkline_data": [
            233.1, 233.4, 233.0, 233.8, 234.2, 234.0, 234.5, 235.0,
            234.8, 235.2, 235.8, 236.1, 235.9, 235.5, 235.2, 234.9,
            234.5, 234.2, 234.0, 234.3, 234.6, 234.7, 234.5, 234.8,
        ],
    },
    "NVDA": {
        "symbol": "NVDA",
        "name": "英伟达 (NVDA)",
        "price": "$141.50",
        "change_24h": "+3.40%",
        "is_up": True,
        "high_24h": "$143.00",
        "low_24h": "$138.20",
        "update_time": "实时分时",
        "sparkline_data": [
            138.5, 138.2, 139.0, 139.8, 140.5, 141.0, 141.8, 142.2,
            142.0, 142.5, 143.0, 142.8, 142.3, 141.9, 141.5, 141.2,
            140.8, 141.1, 141.4, 141.6, 141.8, 141.5, 141.3, 141.5,
        ],
    },
}


async def fetch_stock(symbol: str, custom_name: str | None = None) -> dict[str, Any] | None:
    client = get_async_client()
    minline_url = f"https://stock.finance.sina.com.cn/usstock/api/jsonp.php/var_{symbol}=/US_MinlineService.getMinline?symbol={symbol}"
    qt_url = f"https://qt.gtimg.cn/q=us{symbol}"

    try:
        r_min, r_qt = await asyncio.gather(
            client.get(minline_url, timeout=4.5),
            client.get(qt_url, timeout=4.5),
            return_exceptions=True,
        )
    except Exception as e:
        logger.warning("[StockFetcher] Stock fetch error for %s: %s", symbol, e)
        return None

    name_cn = custom_name or STOCK_NAMES.get(symbol, symbol)
    current_p = 0.0
    pct_change = 0.0
    high_p = 0.0
    low_p = 0.0

    if not isinstance(r_qt, Exception) and r_qt.status_code == 200 and "~" in r_qt.text:
        parts = r_qt.text.split("~")
        if len(parts) > 34:
            name_cn = parts[1] or name_cn
            current_p = float(parts[3])
            pct_change = float(parts[32]) if parts[32] else 0.0
            high_p = float(parts[33]) if parts[33] else current_p
            low_p = float(parts[34]) if parts[34] else current_p

    real_prices: list[float] = []
    if not isinstance(r_min, Exception) and r_min.status_code == 200:
        m = re.search(r"var_" + symbol + r"=\((.*)\);", r_min.text)
        if m:
            try:
                raw_dict = json.loads(m.group(1))
                item = raw_dict.get("minline_1", [{}])[0]
                first_p = float(item.get("first_min", ["", "", "0"])[2] or 0)
                other_pts = [float(p[0]) for p in item.get("other_min", []) if p and p[0]]
                if first_p > 0:
                    real_prices = [first_p] + other_pts
                elif other_pts:
                    real_prices = other_pts
            except Exception as e:
                logger.debug("[StockFetcher] Sina parse error for %s: %s", symbol, e)

    if not real_prices:
        return None

    if current_p <= 0:
        current_p = real_prices[-1]
    if high_p <= 0:
        high_p = max(real_prices)
    if low_p <= 0:
        low_p = min(real_prices)
    if pct_change == 0.0 and len(real_prices) >= 2:
        pct_change = ((real_prices[-1] - real_prices[0]) / real_prices[0]) * 100.0

    sign = "+" if pct_change >= 0 else ""
    return {
        "symbol": symbol,
        "name": f"{name_cn} ({symbol})",
        "price": f"${current_p:,.2f}",
        "change_24h": f"{sign}{pct_change:.2f}%",
        "is_up": pct_change >= 0,
        "high_24h": f"${high_p:,.2f}",
        "low_24h": f"${low_p:,.2f}",
        "update_time": time.strftime("%H:%M"),
        "sparkline_data": downsample(real_prices, 24),
    }
