"""
加密资产市场行情抓取器 (Crypto Market Fetcher)
支持 Binance 与 Gate.io 备用源，包含 24h 涨跌、最高最低与时序 K 线降采样。
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from core.http_client import get_async_client

logger = logging.getLogger(__name__)

CRYPTO_NAMES: dict[str, str] = {
    "BTC": "Bitcoin 比特币",
    "ETH": "Ethereum 以太坊",
    "SOL": "Solana",
    "BNB": "BNB 币安币",
    "DOGE": "Dogecoin 狗狗币",
    "XRP": "XRP 瑞波币",
    "ADA": "Cardano 艾达币",
}

SEED_CRYPTO_DATA: dict[str, dict[str, Any]] = {
    "BTC": {
        "symbol": "BTC/USDT",
        "name": "Bitcoin 比特币",
        "price": "$80,860.00",
        "change_24h": "+3.88%",
        "is_up": True,
        "high_24h": "$81,755.41",
        "low_24h": "$77,615.24",
        "update_time": "实时分时",
        "sparkline_data": [
            77843.3, 77800.1, 77665.3, 77720.0, 78150.0, 78420.5, 78900.2, 79200.0,
            79150.8, 79430.0, 79800.5, 80120.0, 80450.0, 80780.0, 81200.0, 81650.0,
            81755.4, 81520.0, 81300.0, 81100.0, 80950.0, 80890.0, 80820.0, 80860.0,
        ],
    },
    "ETH": {
        "symbol": "ETH/USDT",
        "name": "Ethereum 以太坊",
        "price": "$2,512.40",
        "change_24h": "+4.52%",
        "is_up": True,
        "high_24h": "$2,525.00",
        "low_24h": "$2,393.58",
        "update_time": "实时分时",
        "sparkline_data": [
            2403.7, 2408.2, 2398.5, 2412.0, 2425.8, 2439.0, 2450.2, 2465.0,
            2460.0, 2472.5, 2488.0, 2501.2, 2515.0, 2520.0, 2525.0, 2518.0,
            2510.5, 2505.0, 2508.2, 2512.0, 2515.5, 2510.0, 2509.8, 2512.4,
        ],
    },
    "SOL": {
        "symbol": "SOL/USDT",
        "name": "Solana",
        "price": "$168.50",
        "change_24h": "+6.15%",
        "is_up": True,
        "high_24h": "$171.20",
        "low_24h": "$158.30",
        "update_time": "实时分时",
        "sparkline_data": [
            159.2, 158.8, 158.3, 160.1, 162.0, 163.5, 165.0, 166.2,
            165.8, 167.0, 168.2, 169.5, 170.8, 171.2, 170.5, 169.8,
            169.0, 168.2, 167.9, 168.1, 168.4, 168.6, 168.3, 168.5,
        ],
    },
}


def downsample(prices: list[float], target_points: int = 24) -> list[float]:
    if len(prices) <= target_points:
        return [round(p, 4 if p < 1 else 2) for p in prices]
    step = (len(prices) - 1) / (target_points - 1)
    sampled: list[float] = []
    for i in range(target_points - 1):
        idx = int(round(i * step))
        p = prices[idx]
        sampled.append(round(p, 4 if p < 1 else 2))
    sampled.append(round(prices[-1], 4 if prices[-1] < 1 else 2))
    return sampled


async def fetch_crypto(symbol: str) -> dict[str, Any] | None:
    client = get_async_client()
    binance_kline_url = f"https://data-api.binance.vision/api/v3/klines?symbol={symbol}USDT&interval=1h&limit=24"
    binance_24h_url = f"https://data-api.binance.vision/api/v3/ticker/24hr?symbol={symbol}USDT"

    real_closes: list[float] = []
    last_price = 0.0
    pct_change = 0.0
    high_price = 0.0
    low_price = 0.0

    try:
        r_k, r_t = await asyncio.gather(
            client.get(binance_kline_url, timeout=4.0),
            client.get(binance_24h_url, timeout=4.0),
            return_exceptions=True,
        )
        if not isinstance(r_k, Exception) and r_k.status_code == 200:
            k_data = r_k.json()
            if isinstance(k_data, list) and len(k_data) >= 5:
                real_closes = [float(k[4]) for k in k_data]
        if not isinstance(r_t, Exception) and r_t.status_code == 200:
            t_data = r_t.json()
            last_price = float(t_data.get("lastPrice", 0))
            pct_change = float(t_data.get("priceChangePercent", 0))
            high_price = float(t_data.get("highPrice", 0))
            low_price = float(t_data.get("lowPrice", 0))
    except Exception as e:
        logger.debug("[CryptoFetcher] Binance fetch error for %s: %s", symbol, e)

    # 备用源: Gate.io
    if not real_closes:
        gate_url = f"https://api.gateio.ws/api/v4/spot/candlesticks?currency_pair={symbol}_USDT&interval=1h&limit=24"
        try:
            r_gate = await client.get(gate_url, timeout=4.0)
            if r_gate.status_code == 200:
                gate_data = r_gate.json()
                if isinstance(gate_data, list) and len(gate_data) >= 5:
                    real_closes = [float(k[2]) for k in gate_data]
        except Exception as e:
            logger.debug("[CryptoFetcher] Gate.io fetch error for %s: %s", symbol, e)

    if not real_closes:
        return None

    if last_price <= 0:
        last_price = real_closes[-1]
    if high_price <= 0:
        high_price = max(real_closes)
    if low_price <= 0:
        low_price = min(real_closes)
    if pct_change == 0.0 and len(real_closes) >= 2:
        pct_change = ((real_closes[-1] - real_closes[0]) / real_closes[0]) * 100.0

    fmt_price = f"${last_price:,.2f}" if last_price >= 1 else f"${last_price:,.4f}"
    fmt_high = f"${high_price:,.2f}" if high_price >= 1 else f"${high_price:,.4f}"
    fmt_low = f"${low_price:,.2f}" if low_price >= 1 else f"${low_price:,.4f}"
    sign = "+" if pct_change >= 0 else ""

    return {
        "symbol": f"{symbol}/USDT",
        "name": CRYPTO_NAMES.get(symbol, f"{symbol} Token"),
        "price": fmt_price,
        "change_24h": f"{sign}{pct_change:.2f}%",
        "is_up": pct_change >= 0,
        "high_24h": fmt_high,
        "low_24h": fmt_low,
        "update_time": time.strftime("%H:%M"),
        "sparkline_data": downsample(real_closes, 24),
    }
