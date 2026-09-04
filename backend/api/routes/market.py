"""
市场与金融时序开放 API 路由 (Market & Timeseries API)
提供免 Key、低延迟的标准资产行情与分时时序数据查询。
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Query
from core.market_service import market_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/market", tags=["market"])


@router.get("/summary")
async def get_market_summary(
    symbol: str = Query(default="BTC", description="股票或加密货币代码 (如 BTC, AAPL, TSLA)")
) -> dict[str, Any]:
    """获取综合行情快照（包含当前价格、24h 涨跌幅、极值与 24 点分时走势折线）。"""
    data = await market_service.get_market_data(symbol)
    return {
        "success": True,
        "data": data,
    }


@router.get("/quote")
async def get_market_quote(
    symbol: str = Query(default="BTC", description="资产代码")
) -> dict[str, Any]:
    """获取资产当前实时报价。"""
    data = await market_service.get_market_data(symbol)
    return {
        "success": True,
        "symbol": data.get("symbol"),
        "name": data.get("name"),
        "price": data.get("price"),
        "change_24h": data.get("change_24h"),
        "is_up": data.get("is_up"),
        "high_24h": data.get("high_24h"),
        "low_24h": data.get("low_24h"),
        "update_time": data.get("update_time"),
    }


@router.get("/timeseries")
async def get_market_timeseries(
    symbol: str = Query(default="BTC", description="资产代码")
) -> dict[str, Any]:
    """获取分时真实时序数据点。"""
    data = await market_service.get_market_data(symbol)
    pts = data.get("sparkline_data", [])
    return {
        "success": True,
        "symbol": data.get("symbol"),
        "points_count": len(pts),
        "sparkline_data": pts,
    }


@router.get("/stocks")
async def get_all_stocks() -> dict[str, Any]:
    """获取所有可用股票列表（包含官方内置热门股票与用户添加的持久化自定义股票）。"""
    stocks = market_service.get_all_stocks()
    return {
        "success": True,
        "count": len(stocks),
        "stocks": stocks,
    }


@router.post("/stocks")
async def add_custom_stock(body: dict[str, Any]) -> dict[str, Any]:
    """用户添加一个自定义股票代码并持久化存储（方便下次和所有设备调用）。"""
    symbol = str(body.get("symbol", "")).strip().upper()
    name = str(body.get("name", "")).strip()
    if not symbol:
        return {"success": False, "error": "Symbol cannot be empty"}

    res = await market_service.add_custom_stock(symbol, name)
    return {
        "success": True,
        "stock": {
            "symbol": res["symbol"],
            "name": res["name"],
            "is_custom": True,
        },
    }


@router.delete("/stocks/{symbol}")
async def delete_custom_stock(symbol: str) -> dict[str, Any]:
    """从持久化存储中移除用户添加的股票代码。"""
    removed = market_service.remove_custom_stock(symbol)
    return {
        "success": removed,
        "symbol": symbol.strip().upper(),
    }
