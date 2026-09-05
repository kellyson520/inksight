"""
InkSight 市场与资产时序核心基础设施 (Market & Timeseries Infrastructure Service)
统一调度股票、加密资产与贵金属黄金的实时行情、分时采集、缓存与本地持久化。
底层抓取器已下沉至 core.market 模块。
"""
from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any

from core.market import (
    CRYPTO_NAMES as _CRYPTO_NAMES,
    SEED_CRYPTO_DATA as _SEED_CRYPTO_DATA,
    STOCK_SYMBOLS as _STOCK_SYMBOLS,
    STOCK_NAMES as _STOCK_NAMES,
    SEED_STOCK_DATA as _SEED_STOCK_DATA,
    GOLD_SYMBOLS as _GOLD_SYMBOLS,
    GOLD_NAMES as _GOLD_NAMES,
    SEED_GOLD_DATA as _SEED_GOLD_DATA,
    downsample as _downsample_fn,
    fetch_crypto,
    fetch_stock,
    fetch_gold,
)

logger = logging.getLogger(__name__)

# 基础目录与持久化快照文件
_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_CACHE_FILE = _DATA_DIR / "real_market_cache.json"
_CUSTOM_STOCKS_FILE = _DATA_DIR / "custom_stocks.json"

_SEED_MARKET_DATA: dict[str, dict[str, Any]] = {
    **_SEED_GOLD_DATA,
    **_SEED_CRYPTO_DATA,
    **_SEED_STOCK_DATA,
}


class MarketService:
    """统一行情调度与缓存持久化服务。"""

    def __init__(self, ttl: float = 60.0) -> None:
        self._ttl = ttl
        self._cache: dict[str, tuple[float, dict[str, Any]]] = {}
        self._persisted: dict[str, dict[str, Any]] = {}
        self._custom_stocks: dict[str, str] = {}
        self._load_custom_stocks()
        self._load_persisted()

    def _load_custom_stocks(self) -> None:
        try:
            if _CUSTOM_STOCKS_FILE.exists():
                data = json.loads(_CUSTOM_STOCKS_FILE.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    self._custom_stocks = {k.upper(): str(v) for k, v in data.items()}
        except Exception as e:
            logger.warning("[MarketService] Failed to load custom stocks: %s", e)

    def _save_custom_stocks(self) -> None:
        try:
            _DATA_DIR.mkdir(parents=True, exist_ok=True)
            _CUSTOM_STOCKS_FILE.write_text(
                json.dumps(self._custom_stocks, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception as e:
            logger.warning("[MarketService] Failed to save custom stocks: %s", e)

    def _load_persisted(self) -> None:
        try:
            if _CACHE_FILE.exists():
                data = json.loads(_CACHE_FILE.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    self._persisted = data
                    now = time.time()
                    for k, v in data.items():
                        self._cache[k] = (now, v)
        except Exception as e:
            logger.warning("[MarketService] Failed to load persisted market cache: %s", e)

    def _save_persisted(self) -> None:
        try:
            _DATA_DIR.mkdir(parents=True, exist_ok=True)
            _CACHE_FILE.write_text(
                json.dumps(self._persisted, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception as e:
            logger.warning("[MarketService] Failed to save persisted cache: %s", e)

    @staticmethod
    def _downsample(prices: list[float], target_points: int = 24) -> list[float]:
        return _downsample_fn(prices, target_points)

    def normalize_symbol(self, raw_symbol: str) -> str:
        sym = raw_symbol.strip().upper()
        return sym.replace("/USDT", "").replace("USDT", "").strip() or "BTC"

    def get_supported_stocks(self) -> list[dict[str, Any]]:
        result = []
        for sym in sorted(_STOCK_SYMBOLS):
            result.append({
                "symbol": sym,
                "name": _STOCK_NAMES.get(sym, sym),
                "is_custom": False,
            })
        for sym, name in sorted(self._custom_stocks.items()):
            if sym not in _STOCK_SYMBOLS:
                result.append({
                    "symbol": sym,
                    "name": name,
                    "is_custom": True,
                })
        return result

    def get_all_stocks(self) -> list[dict[str, Any]]:
        return self.get_supported_stocks()

    async def add_custom_stock(self, symbol: str, name: str) -> dict[str, Any]:
        clean_sym = symbol.strip().upper()
        clean_name = name.strip()
        if not clean_sym or not clean_name:
            raise ValueError("Invalid symbol or name")
        self._custom_stocks[clean_sym] = clean_name
        self._save_custom_stocks()
        return {"symbol": clean_sym, "name": clean_name}

    def remove_custom_stock(self, symbol: str) -> bool:
        clean_sym = symbol.strip().upper()
        if clean_sym in self._custom_stocks:
            del self._custom_stocks[clean_sym]
            self._save_custom_stocks()
            return True
        return False

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
            custom_name = self._custom_stocks.get(sym)
            res = await fetch_stock(sym, custom_name=custom_name)
        elif is_known_crypto:
            res = await fetch_crypto(sym)

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
            res = await fetch_gold(sym)
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


# 全局单例
market_service = MarketService()
