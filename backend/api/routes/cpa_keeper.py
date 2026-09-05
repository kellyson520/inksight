"""
CPA 与 Keeper 容器额度监控与统计 API
"""
from __future__ import annotations

from typing import Any
from fastapi import APIRouter
from core.cpa_keeper_service import cpa_keeper_service

router = APIRouter(prefix="/cpa-keeper", tags=["cpa-keeper"])


@router.get("/overview")
async def get_cpa_keeper_overview() -> dict[str, Any]:
    """获取 CPA 代理与 Keeper 容器的综合额度与消耗统计。"""
    metrics = cpa_keeper_service.get_aggregated_metrics(force_refresh=True)
    return {
        "success": True,
        "data": metrics,
    }


@router.get("/health")
async def get_cpa_keeper_health() -> dict[str, Any]:
    """获取 CPA 与 Keeper 容器的健康探针状态。"""
    health = cpa_keeper_service.check_health()
    return {
        "success": True,
        "health": health,
    }
