"""
全网热点聚合开放 API 路由 (Hotlist API)
提供知乎、微博、B站、GitHub Trending 等热门榜单查询。
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Path, Query
from core.hotlist_service import hotlist_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/hotlist", tags=["hotlist"])


@router.get("/platforms")
async def get_supported_platforms() -> dict[str, Any]:
    """获取所有支持的热榜平台列表。"""
    return {
        "success": True,
        "platforms": [
            {"id": "zhihu", "name": "知乎今日热榜"},
            {"id": "weibo", "name": "微博实时热搜"},
            {"id": "bilibili", "name": "哔哩哔哩热播推荐"},
            {"id": "github", "name": "GitHub Trending 今日热门"},
            {"id": "baidu", "name": "百度今日热搜"},
        ],
    }


@router.get("/{platform}")
async def get_platform_hotlist(
    platform: str = Path(..., description="平台代码 (zhihu, weibo, bilibili, github, baidu)"),
    limit: int = Query(default=5, ge=1, le=20, description="获取条数"),
) -> dict[str, Any]:
    """获取指定平台的实时热榜数据。"""
    data = await hotlist_service.get_hotlist(platform, limit=limit)
    return {
        "success": True,
        "data": data,
    }
