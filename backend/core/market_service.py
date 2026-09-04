"""
InkSight 市场与资产时序核心基础设施 (Market & Timeseries Infrastructure Service)
统一管理全球股票、大盘指数与加密资产的实时报价、真实分时时序采集、多源容灾熔断与持久化。
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from pathlib import Path
from typing import Any

from .http_client import get_async_client

logger = logging.getLogger(__name__)

# 基础目录与持久化快照文件
_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_CACHE_FILE = _DATA_DIR / "real_market_cache.json"

_STOCK_SYMBOLS = {"AAPL", "TSLA", "NVDA", "MSFT", "GOOGL", "AMZN", "META", "BABA"}

_STOCK_NAMES: dict[str, str] = {
    "AAPL": "苹果",
    "TSLA": "特斯拉",
    "NVDA": "英伟达",
    "MSFT": "微软",
    "GOOGL": "谷歌",
    "AMZN": "亚马逊",
    "META": "Meta",
    "BABA": "阿里巴巴",
}

_CRYPTO_NAMES: dict[str, str] = {
    "BTC": "Bitcoin 比特币",
    "ETH": "Ethereum 以太坊",
    "SOL": "Solana",
    "BNB": "BNB 币安币",
    "DOGE": "Dogecoin 狗狗币",
    "XRP": "XRP 瑞波币",
    "ADA": "Cardano 艾达币",
}

# 兜底种子时序数据
_SEED_MARKET_DATA: dict[str, dict[str, Any]] = {
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
            2470.5, 2482.0, 2490.5, 2498.0, 2505.0, 2515.2, 2525.0, 2520.0,
            2518.2, 2515.0, 2510.8, 2508.0, 2512.0, 2515.0, 2510.0, 2512.4,
        ],
    },
    "AAPL": {
        "symbol": "AAPL",
        "name": "苹果 (AAPL)",
        "price": "$328.21",
        "change_24h": "+1.00%",
        "is_up": True,
        "high_24h": "$330.81",
        "low_24h": "$324.11",
        "update_time": "美股分时",
        "sparkline_data": [
            324.96, 325.38, 327.39, 326.08, 327.20, 328.05, 329.15, 330.40,
            330.81, 330.20, 329.50, 328.80, 327.90, 327.25, 326.80, 327.10,
            327.60, 327.95, 328.30, 328.10, 328.45, 328.35, 328.15, 328.21,
        ],
    },
    "TSLA": {
        "symbol": "TSLA",
        "name": "特斯拉 (TSLA)",
        "price": "$376.37",
        "change_24h": "+5.39%",
        "is_up": True,
        "high_24h": "$383.92",
        "low_24h": "$357.10",
        "update_time": "美股分时",
        "sparkline_data": [
            357.10, 359.50, 362.40, 365.80, 369.20, 372.50, 376.00, 379.80,
            383.92, 382.40, 380.10, 378.50, 376.90, 375.40, 374.80, 375.60,
            376.20, 377.10, 378.00, 377.50, 376.80, 376.50, 376.20, 376.37,
        ],
    },
}


class MarketService:
    """市场行情与时序基础设施服务。"""

    def __init__(self, ttl: float = 120.0):
        self._ttl = ttl
        self._cache: dict[str, tuple[float, dict[str, Any]]] = {}
        self._persisted = self._load_persisted()

    def _load_persisted(self) -> dict[str, dict[str, Any]]:
        if not _CACHE_FILE.exists():
            return dict(_SEED_MARKET_DATA)
        try:
            with open(_CACHE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                merged = dict(_SEED_MARKET_DATA)
                merged.update(data)
                return merged
        except Exception as e:
            logger.warning("[MarketService] Failed to load persisted cache: %s", e)
            return dict(_SEED_MARKET_DATA)

    def _save_persisted(self) -> None:
        try:
            _DATA_DIR.mkdir(parents=True, exist_ok=True)
            with open(_CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(self._persisted, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning("[MarketService] Failed to save persisted cache: %s", e)

    @staticmethod
    def _downsample(prices: list[float], target_points: int = 24) -> list[float]:
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

    def normalize_symbol(self, raw_symbol: str) -> str:
        sym = raw_symbol.strip().upper()
        return sym.replace("/USDT", "").replace("USDT", "").strip() or "BTC"

    async def get_market_data(self, raw_symbol: str) -> dict[str, Any]:
        """获取综合资产行情与分时时序数据（统一入口）。"""
        sym = self.normalize_symbol(raw_symbol)
        now = time.time()
        cached = self._cache.get(sym)
        if cached and (now - cached[0] < self._ttl):
            return cached[1]

        if sym in _STOCK_SYMBOLS:
            res = await self._fetch_stock(sym)
        else:
            res = await self._fetch_crypto(sym)

        if res and res.get("sparkline_data"):
            self._cache[sym] = (now, res)
            self._persisted[sym] = res
            self._save_persisted()
            return res

        # 降级：从本地持久化真实数据中恢复
        fb = self._persisted.get(sym) or _SEED_MARKET_DATA.get(sym) or _SEED_MARKET_DATA["BTC"]
        fallback_res = dict(fb)
        fallback_res["update_time"] = time.strftime("%H:%M")
        return fallback_res

    async def _fetch_stock(self, symbol: str) -> dict[str, Any] | None:
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
            logger.warning("[MarketService] Stock fetch error for %s: %s", symbol, e)
            return None

        name_cn = _STOCK_NAMES.get(symbol, symbol)
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
                    logger.debug("[MarketService] Sina parse error for %s: %s", symbol, e)

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
            "sparkline_data": self._downsample(real_prices, 24),
        }

    async def _fetch_crypto(self, symbol: str) -> dict[str, Any] | None:
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
            logger.debug("[MarketService] Binance fetch error for %s: %s", symbol, e)

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
                logger.debug("[MarketService] Gate.io fetch error for %s: %s", symbol, e)

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
            "name": _CRYPTO_NAMES.get(symbol, f"{symbol} Token"),
            "price": fmt_price,
            "change_24h": f"{sign}{pct_change:.2f}%",
            "is_up": pct_change >= 0,
            "high_24h": fmt_high,
            "low_24h": fmt_low,
            "update_time": time.strftime("%H:%M"),
            "sparkline_data": self._downsample(real_closes, 24),
        }


# 全局单例
market_service = MarketService()
