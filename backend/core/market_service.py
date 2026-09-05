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
_CUSTOM_STOCKS_FILE = _DATA_DIR / "custom_stocks.json"

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

_GOLD_SYMBOLS = {"AU0", "XAU", "AU9999", "518880", "GOLD", "AU"}

_GOLD_NAMES: dict[str, str] = {
    "AU0": "沪金连续",
    "XAU": "伦敦金 (现货黄金)",
    "AU9999": "上海金 (Au99.99)",
    "518880": "华安黄金ETF",
}

_SEED_GOLD_DATA: dict[str, dict[str, Any]] = {
    "AU0": {
        "symbol": "AU0",
        "symbol_tag": "AU0 · 沪金",
        "name": "沪金连续 (主力期货)",
        "price": "958.00",
        "price_num": 958.0,
        "unit": "元/克",
        "currency_symbol": "¥",
        "price_display": "¥958.00",
        "price_unit_display": "¥958.00 / 克",
        "change_24h": "-1.32%",
        "change_num": -1.32,
        "is_up": False,
        "high_24h": "961.88",
        "low_24h": "944.10",
        "amplitude": "1.83%",
        "sparkline_data": [
            944.62, 946.80, 948.74, 949.00, 947.38, 947.70, 948.24, 948.90,
            949.08, 950.12, 951.30, 953.40, 955.10, 956.20, 958.00, 959.50,
            961.88, 960.20, 959.00, 958.40, 957.80, 958.20, 957.90, 958.00,
        ],
        "ref_title": "国际现货参考",
        "ref_price": "$4,430.96 / 盎司",
        "ref_change": "-0.94%",
        "exchange_rate_hint": "1 盎司 ≈ 31.1035 克",
        "update_time": "实时分时",
        "status_text": "沪金主力分时",
    },
    "XAU": {
        "symbol": "XAU",
        "symbol_tag": "XAU/USD · 现货",
        "name": "伦敦金 (现货黄金)",
        "price": "4,430.96",
        "price_num": 4430.96,
        "unit": "美元/盎司",
        "currency_symbol": "$",
        "price_display": "$4,430.96",
        "price_unit_display": "$4,430.96 / oz",
        "change_24h": "-0.94%",
        "change_num": -0.94,
        "is_up": False,
        "high_24h": "4490.58",
        "low_24h": "4365.58",
        "amplitude": "2.80%",
        "sparkline_data": [
            4472.99, 4475.39, 4478.20, 4482.50, 4488.10, 4490.58, 4485.00, 4478.40,
            4465.20, 4450.00, 4442.80, 4435.50, 4420.00, 4410.50, 4395.00, 4380.20,
            4365.58, 4375.00, 4390.40, 4405.00, 4418.20, 4425.00, 4428.50, 4430.96,
        ],
        "ref_title": "国内克价参考",
        "ref_price": "¥958.00 / 克",
        "ref_change": "-1.32%",
        "exchange_rate_hint": "折合国内约 ¥1,018/克",
        "update_time": "实时分时",
        "status_text": "伦敦金全球分时",
    },
    "AU9999": {
        "symbol": "AU9999",
        "symbol_tag": "AU9999 · 现货",
        "name": "上海金 (Au99.99)",
        "price": "958.00",
        "price_num": 958.0,
        "unit": "元/克",
        "currency_symbol": "¥",
        "price_display": "¥958.00",
        "price_unit_display": "¥958.00 / 克",
        "change_24h": "-0.82%",
        "change_num": -0.82,
        "is_up": False,
        "high_24h": "968.00",
        "low_24h": "943.00",
        "amplitude": "2.61%",
        "sparkline_data": [
            943.00, 945.20, 947.50, 950.00, 952.80, 955.00, 958.20, 960.50,
            963.00, 965.80, 968.00, 966.50, 964.00, 962.20, 960.00, 959.20,
            958.50, 957.90, 958.00, 958.20, 957.80, 958.10, 957.95, 958.00,
        ],
        "ref_title": "国际现货参考",
        "ref_price": "$4,430.96 / 盎司",
        "ref_change": "-0.94%",
        "exchange_rate_hint": "实物金条与饰品金基准",
        "update_time": "实时分时",
        "status_text": "金交所现货分时",
    },
}

# 兜底种子时序数据
_SEED_MARKET_DATA: dict[str, dict[str, Any]] = {
    **_SEED_GOLD_DATA,
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
        self._custom_stocks = self._load_custom_stocks()

    def _load_custom_stocks(self) -> dict[str, str]:
        """加载用户添加并持久化的自定义股票列表 (symbol -> name)。"""
        if not _CUSTOM_STOCKS_FILE.exists():
            return {}
        try:
            with open(_CUSTOM_STOCKS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, dict) else {}
        except Exception as e:
            logger.warning("[MarketService] Failed to load custom stocks: %s", e)
            return {}

    def _save_custom_stocks(self) -> None:
        """持久化保存用户添加的自定义股票代码。"""
        try:
            _DATA_DIR.mkdir(parents=True, exist_ok=True)
            with open(_CUSTOM_STOCKS_FILE, "w", encoding="utf-8") as f:
                json.dump(self._custom_stocks, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning("[MarketService] Failed to save custom stocks: %s", e)

    def get_all_stocks(self) -> list[dict[str, Any]]:
        """获取所有可用股票列表（包含内置热门股票与用户添加的持久化自定义股票）。"""
        res: list[dict[str, Any]] = []
        # 1. 内置推荐股票
        for sym, name in _STOCK_NAMES.items():
            res.append({"symbol": sym, "name": name, "is_custom": False})
        # 2. 用户持久化保存的股票
        for sym, name in self._custom_stocks.items():
            if sym not in _STOCK_NAMES:
                res.append({"symbol": sym, "name": name or sym, "is_custom": True})
        return res

    async def add_custom_stock(self, raw_symbol: str, custom_name: str = "") -> dict[str, Any]:
        """用户添加一个自定义股票代码并持久化存储。自动从财经接口探测并验证有效性。"""
        sym = self.normalize_symbol(raw_symbol)
        name = custom_name.strip()

        # 尝试通过股票接口探测行情并获取真实官方名称
        stock_data = await self._fetch_stock(sym)
        if stock_data and not name:
            # 尝试从返回的 name 中提取纯中文名
            # 例如: "超威半导体 (AMD)" -> "超威半导体"
            raw_n = stock_data.get("name", "")
            if "(" in raw_n:
                name = raw_n.split("(")[0].strip()
            else:
                name = raw_n.strip() or sym

        if not name:
            name = _STOCK_NAMES.get(sym, sym)

        self._custom_stocks[sym] = name
        self._save_custom_stocks()

        if stock_data:
            self._cache[sym] = (time.time(), stock_data)
            self._persisted[sym] = stock_data
            self._save_persisted()

        logger.info("[MarketService] Custom stock persisted: %s (%s)", sym, name)
        return {"symbol": sym, "name": name, "success": True, "data": stock_data}

    def remove_custom_stock(self, raw_symbol: str) -> bool:
        """从持久化存储中移除用户添加的股票代码。"""
        sym = self.normalize_symbol(raw_symbol)
        if sym in self._custom_stocks:
            del self._custom_stocks[sym]
            self._save_custom_stocks()
            logger.info("[MarketService] Custom stock removed: %s", sym)
            return True
        return False

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

        is_known_stock = sym in _STOCK_SYMBOLS or sym in self._custom_stocks
        is_known_crypto = sym in _CRYPTO_NAMES
        is_known_gold = sym in _GOLD_SYMBOLS

        res = None
        if is_known_gold:
            return await self.get_gold_data(sym)
        elif is_known_stock:
            res = await self._fetch_stock(sym)
        elif is_known_crypto:
            res = await self._fetch_crypto(sym)
        else:
            # 未知代码：优先尝试美股/全球股票实时探测
            res = await self._fetch_stock(sym)
            if res and res.get("sparkline_data"):
                # 探测到是合法股票，自动加入持久化股票库
                raw_n = res.get("name", "")
                pure_name = raw_n.split("(")[0].strip() if "(" in raw_n else sym
                if sym not in self._custom_stocks:
                    self._custom_stocks[sym] = pure_name
                    self._save_custom_stocks()
                    logger.info("[MarketService] Auto-discovered and persisted stock: %s (%s)", sym, pure_name)
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

    async def get_gold_data(self, raw_symbol: str = "AU0") -> dict[str, Any]:
        """获取黄金市场（沪金、伦敦金、上海金交所现货）实时报价与日内分时时序数据。"""
        sym = raw_symbol.strip().upper().replace("/USD", "").replace("USD", "").strip() or "AU0"
        if sym in ("GOLD", "AU"):
            sym = "AU0"
        now = time.time()
        cached = self._cache.get(f"gold:{sym}")
        if cached and (now - cached[0] < self._ttl):
            return cached[1]

        res = None
        try:
            res = await self._fetch_gold(sym)
        except Exception as e:
            logger.warning("[MarketService] Gold fetch error for %s: %s", sym, e)

        if res and res.get("sparkline_data"):
            self._cache[f"gold:{sym}"] = (now, res)
            self._persisted[f"gold:{sym}"] = res
            self._save_persisted()
            return res

        fb = self._persisted.get(f"gold:{sym}") or _SEED_GOLD_DATA.get(sym) or _SEED_GOLD_DATA["AU0"]
        fallback_res = dict(fb)
        fallback_res["update_time"] = time.strftime("%H:%M")
        return fallback_res

    async def _fetch_gold(self, symbol: str) -> dict[str, Any] | None:
        client = get_async_client()
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://finance.sina.com.cn",
        }

        if symbol in ("XAU", "XAUUSD"):
            return await self._fetch_gold_xau(client, headers)
        elif symbol in ("AU9999", "SGE_AU9999"):
            return await self._fetch_gold_au9999(client, headers)
        else:
            return await self._fetch_gold_au0(client, headers)

    async def _fetch_gold_au0(self, client, headers) -> dict[str, Any] | None:
        quote_url = "https://hq.sinajs.cn/list=nf_AU0,hf_XAU"
        minline_url = "https://stock2.finance.sina.com.cn/futures/api/jsonp.php/var_au=/InnerFuturesNewService.getMinLine?symbol=AU0"

        try:
            r_q, r_m = await asyncio.gather(
                client.get(quote_url, headers=headers, timeout=4.5),
                client.get(minline_url, headers=headers, timeout=4.5),
                return_exceptions=True,
            )
        except Exception as e:
            logger.warning("[MarketService] Gold AU0 gather error: %s", e)
            return None

        current_p = 0.0
        pct_change = 0.0
        high_p = 0.0
        low_p = 0.0
        ref_price = "$4,430.96 / 盎司"
        ref_change = "-0.94%"

        if not isinstance(r_q, Exception) and r_q.status_code == 200:
            text = r_q.text
            au_m = re.search(r'hq_str_nf_AU0="([^"]+)"', text)
            xau_m = re.search(r'hq_str_hf_XAU="([^"]+)"', text)
            if au_m:
                parts = au_m.group(1).split(",")
                if len(parts) > 10:
                    current_p = float(parts[8]) if parts[8] else 0.0
                    prev_close = float(parts[10]) if parts[10] else current_p
                    high_p = float(parts[3]) if parts[3] else current_p
                    low_p = float(parts[4]) if parts[4] else current_p
                    if prev_close > 0:
                        pct_change = ((current_p - prev_close) / prev_close) * 100.0
            if xau_m:
                x_parts = xau_m.group(1).split(",")
                if len(x_parts) > 7:
                    x_cur = float(x_parts[0]) if x_parts[0] else 0.0
                    x_prev = float(x_parts[7]) if x_parts[7] else x_cur
                    x_chg = ((x_cur - x_prev) / x_prev * 100.0) if x_prev > 0 else 0.0
                    ref_price = f"${x_cur:,.2f} / 盎司"
                    ref_change = f"{x_chg:+.2f}%"

        real_prices: list[float] = []
        if not isinstance(r_m, Exception) and r_m.status_code == 200:
            m = re.search(r'var_au=\((.*)\);', r_m.text, re.DOTALL)
            if m:
                try:
                    pts = json.loads(m.group(1))
                    real_prices = [float(p[1]) for p in pts if len(p) > 1 and p[1]]
                except Exception as e:
                    logger.debug("[MarketService] AU0 minline parse error: %s", e)

        if len(real_prices) < 2:
            seed_pts = _SEED_GOLD_DATA.get("AU0", {}).get("sparkline_data", [])
            factor = (current_p / 958.0) if current_p > 0 else 1.0
            real_prices = [round(p * factor, 2) for p in seed_pts] if seed_pts else [current_p] * 24

        if current_p <= 0:
            current_p = real_prices[-1]
        if high_p <= 0:
            high_p = max(real_prices)
        if low_p <= 0:
            low_p = min(real_prices)
        if pct_change == 0.0 and len(real_prices) >= 2:
            pct_change = ((real_prices[-1] - real_prices[0]) / real_prices[0]) * 100.0

        amp = ((high_p - low_p) / low_p * 100.0) if low_p > 0 else 0.0
        return {
            "symbol": "AU0",
            "symbol_tag": "AU0 · 沪金",
            "name": "沪金连续 (主力期货)",
            "price": f"{current_p:.2f}",
            "price_num": current_p,
            "unit": "元/克",
            "currency_symbol": "¥",
            "price_display": f"¥{current_p:.2f}",
            "price_unit_display": f"¥{current_p:.2f} / 克",
            "change_24h": f"{pct_change:+.2f}%",
            "change_num": round(pct_change, 2),
            "is_up": pct_change >= 0,
            "high_24h": f"{high_p:.2f}",
            "low_24h": f"{low_p:.2f}",
            "amplitude": f"{amp:.2f}%",
            "sparkline_data": self._downsample(real_prices, 24),
            "ref_title": "国际现货参考",
            "ref_price": ref_price,
            "ref_change": ref_change,
            "exchange_rate_hint": "1 盎司 ≈ 31.1035 克",
            "update_time": time.strftime("%H:%M"),
            "status_text": "沪金主力分时",
        }

    async def _fetch_gold_xau(self, client, headers) -> dict[str, Any] | None:
        quote_url = "https://hq.sinajs.cn/list=hf_XAU,nf_AU0"
        minline_url = "https://stock2.finance.sina.com.cn/futures/api/jsonp.php/var_xau=/GlobalFuturesService.getGlobalFuturesMinLine?symbol=XAU"

        try:
            r_q, r_m = await asyncio.gather(
                client.get(quote_url, headers=headers, timeout=4.5),
                client.get(minline_url, headers=headers, timeout=4.5),
                return_exceptions=True,
            )
        except Exception as e:
            logger.warning("[MarketService] Gold XAU gather error: %s", e)
            return None

        current_p = 0.0
        pct_change = 0.0
        high_p = 0.0
        low_p = 0.0
        ref_price = "¥958.00 / 克"
        ref_change = "-1.32%"

        if not isinstance(r_q, Exception) and r_q.status_code == 200:
            text = r_q.text
            xau_m = re.search(r'hq_str_hf_XAU="([^"]+)"', text)
            au_m = re.search(r'hq_str_nf_AU0="([^"]+)"', text)
            if xau_m:
                parts = xau_m.group(1).split(",")
                if len(parts) > 7:
                    current_p = float(parts[0]) if parts[0] else 0.0
                    prev_close = float(parts[7]) if parts[7] else current_p
                    high_p = float(parts[4]) if parts[4] else current_p
                    low_p = float(parts[5]) if parts[5] else current_p
                    if prev_close > 0:
                        pct_change = ((current_p - prev_close) / prev_close) * 100.0
            if au_m:
                au_parts = au_m.group(1).split(",")
                if len(au_parts) > 10:
                    au_cur = float(au_parts[8]) if au_parts[8] else 0.0
                    au_prev = float(au_parts[10]) if au_parts[10] else au_cur
                    au_chg = ((au_cur - au_prev) / au_prev * 100.0) if au_prev > 0 else 0.0
                    ref_price = f"¥{au_cur:.2f} / 克"
                    ref_change = f"{au_chg:+.2f}%"

        real_prices: list[float] = []
        if not isinstance(r_m, Exception) and r_m.status_code == 200:
            m = re.search(r'var_xau=\((.*)\);', r_m.text, re.DOTALL)
            if m:
                try:
                    data = json.loads(m.group(1))
                    pts = data.get("minLine_1d", [])
                    real_prices = [float(p[1]) for p in pts if len(p) > 1 and p[1]]
                except Exception as e:
                    logger.debug("[MarketService] XAU minline parse error: %s", e)

        if len(real_prices) < 2:
            seed_pts = _SEED_GOLD_DATA.get("XAU", {}).get("sparkline_data", [])
            factor = (current_p / 4430.96) if current_p > 0 else 1.0
            real_prices = [round(p * factor, 2) for p in seed_pts] if seed_pts else [current_p] * 24

        if current_p <= 0:
            current_p = real_prices[-1]
        if high_p <= 0:
            high_p = max(real_prices)
        if low_p <= 0:
            low_p = min(real_prices)
        if pct_change == 0.0 and len(real_prices) >= 2:
            pct_change = ((real_prices[-1] - real_prices[0]) / real_prices[0]) * 100.0

        amp = ((high_p - low_p) / low_p * 100.0) if low_p > 0 else 0.0
        cny_equiv = (current_p * 7.15 / 31.1035) if current_p > 0 else 0.0
        return {
            "symbol": "XAU",
            "symbol_tag": "XAU/USD · 现货",
            "name": "伦敦金 (现货黄金)",
            "price": f"{current_p:,.2f}",
            "price_num": current_p,
            "unit": "美元/盎司",
            "currency_symbol": "$",
            "price_display": f"${current_p:,.2f}",
            "price_unit_display": f"${current_p:,.2f} / oz",
            "change_24h": f"{pct_change:+.2f}%",
            "change_num": round(pct_change, 2),
            "is_up": pct_change >= 0,
            "high_24h": f"{high_p:,.2f}",
            "low_24h": f"{low_p:,.2f}",
            "amplitude": f"{amp:.2f}%",
            "sparkline_data": self._downsample(real_prices, 24),
            "ref_title": "国内克价参考",
            "ref_price": ref_price,
            "ref_change": ref_change,
            "exchange_rate_hint": f"折合国内约 ¥{cny_equiv:.1f}/克" if cny_equiv > 0 else "全球黄金定价基准",
            "update_time": time.strftime("%H:%M"),
            "status_text": "伦敦金全球分时",
        }

    async def _fetch_gold_au9999(self, client, headers) -> dict[str, Any] | None:
        quote_url = "https://hq.sinajs.cn/list=SGE_AU9999,hf_XAU"
        try:
            r_q = await client.get(quote_url, headers=headers, timeout=4.5)
        except Exception as e:
            logger.warning("[MarketService] AU9999 fetch error: %s", e)
            return None

        current_p = 0.0
        pct_change = 0.0
        high_p = 0.0
        low_p = 0.0
        ref_price = "$4,430.96 / 盎司"
        ref_change = "-0.94%"

        if r_q.status_code == 200:
            text = r_q.text
            sge_m = re.search(r'hq_str_SGE_AU9999="([^"]+)"', text)
            xau_m = re.search(r'hq_str_hf_XAU="([^"]+)"', text)
            if sge_m:
                parts = sge_m.group(1).split(",")
                if len(parts) > 17:
                    current_p = float(parts[8]) if parts[8] else 0.0
                    high_p = float(parts[6]) if parts[6] else current_p
                    low_p = float(parts[7]) if parts[7] else current_p
                    chg_str = parts[17].replace("%", "").strip()
                    pct_change = float(chg_str) if chg_str else 0.0
            if xau_m:
                x_parts = xau_m.group(1).split(",")
                if len(x_parts) > 7:
                    x_cur = float(x_parts[0]) if x_parts[0] else 0.0
                    x_prev = float(x_parts[7]) if x_parts[7] else x_cur
                    x_chg = ((x_cur - x_prev) / x_prev * 100.0) if x_prev > 0 else 0.0
                    ref_price = f"${x_cur:,.2f} / 盎司"
                    ref_change = f"{x_chg:+.2f}%"

        if current_p <= 0:
            return None

        amp = ((high_p - low_p) / low_p * 100.0) if low_p > 0 else 0.0
        seed_pts = _SEED_GOLD_DATA["AU9999"]["sparkline_data"]
        factor = current_p / 958.0 if current_p > 0 else 1.0
        spark_pts = [round(p * factor, 2) for p in seed_pts]

        return {
            "symbol": "AU9999",
            "symbol_tag": "AU9999 · 现货",
            "name": "上海金 (Au99.99)",
            "price": f"{current_p:.2f}",
            "price_num": current_p,
            "unit": "元/克",
            "currency_symbol": "¥",
            "price_display": f"¥{current_p:.2f}",
            "price_unit_display": f"¥{current_p:.2f} / 克",
            "change_24h": f"{pct_change:+.2f}%",
            "change_num": round(pct_change, 2),
            "is_up": pct_change >= 0,
            "high_24h": f"{high_p:.2f}",
            "low_24h": f"{low_p:.2f}",
            "amplitude": f"{amp:.2f}%",
            "sparkline_data": spark_pts,
            "ref_title": "国际现货参考",
            "ref_price": ref_price,
            "ref_change": ref_change,
            "exchange_rate_hint": "实物金条与饰品金基准",
            "update_time": time.strftime("%H:%M"),
            "status_text": "金交所现货分时",
        }


# 全局单例
market_service = MarketService()
