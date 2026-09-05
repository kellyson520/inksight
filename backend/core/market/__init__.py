"""
金融与行情市场抓取基础设施包 (Market Data Infrastructure Package)
包含加密资产、股票、贵金属黄金独立抓取器与时序下采样工具。
"""
from .crypto_fetcher import (
    CRYPTO_NAMES,
    SEED_CRYPTO_DATA,
    downsample,
    fetch_crypto,
)
from .stock_fetcher import (
    STOCK_SYMBOLS,
    STOCK_NAMES,
    SEED_STOCK_DATA,
    fetch_stock,
)
from .gold_fetcher import (
    GOLD_SYMBOLS,
    GOLD_NAMES,
    SEED_GOLD_DATA,
    fetch_gold,
)

__all__ = [
    "CRYPTO_NAMES",
    "SEED_CRYPTO_DATA",
    "STOCK_SYMBOLS",
    "STOCK_NAMES",
    "SEED_STOCK_DATA",
    "GOLD_SYMBOLS",
    "GOLD_NAMES",
    "SEED_GOLD_DATA",
    "downsample",
    "fetch_crypto",
    "fetch_stock",
    "fetch_gold",
]
