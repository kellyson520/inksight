"""
服务器与主机性能监控 API (Server Status API)
支持接收 Linux 宿主机、宝塔面板或 VPS 探针脚本定期上报的系统健康状态，并提供监控脚本生成与指标查询。
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from fastapi import APIRouter, Header, Query, Request, Response
from fastapi.responses import PlainTextResponse
from core.server_status_service import server_status_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/server-status", tags=["server-status"])


@router.get("")
async def get_server_status(
    key: Optional[str] = Query(default=None, description="服务器标识 key (留空返回当前宿主机或最新上报数据)")
) -> dict[str, Any]:
    """获取当前服务器性能指标。"""
    metrics = server_status_service.get_metrics_for_mode(key)
    custom_name = server_status_service.get_server_name(key)
    return {
        "success": True,
        "metrics": metrics,
        "custom_name": custom_name,
    }


@router.post("/rename")
async def rename_server(payload: dict[str, Any]) -> dict[str, Any]:
    """持久化修改服务器显示名称/别名。"""
    key = str(payload.get("key") or payload.get("server_key") or "default").strip()
    name = str(payload.get("server_name") or payload.get("name") or "").strip()
    if not name:
        return {"success": False, "error": "Server name cannot be empty"}
    persisted_name = server_status_service.set_server_name(key, name)
    return {
        "success": True,
        "key": key,
        "server_name": persisted_name,
        "message": "服务器名称已成功持久化保存",
    }


@router.post("")
async def report_server_status(
    payload: dict[str, Any],
    key: Optional[str] = Query(default=None, description="服务器标识 key (如 vps-hk, homelab)"),
    x_server_key: Optional[str] = Header(default=None, alias="X-Server-Key"),
) -> dict[str, Any]:
    """接收外部探针、宝塔计划任务或 Cron 脚本上报的服务器性能数据。"""
    target_key = (key or x_server_key or payload.get("server_name") or "default").strip()
    result = server_status_service.record_pushed_metrics(target_key, payload)
    return {
        "success": True,
        "key": target_key,
        "received": result,
    }


@router.get("/script", response_class=PlainTextResponse)
async def get_reporting_script(
    request: Request,
    key: Optional[str] = Query(default="", description="服务器名称/标识"),
) -> str:
    """生成一键复制运行的上报 Shell 脚本。"""
    host = (
        request.headers.get("x-forwarded-host")
        or request.headers.get("host")
        or request.url.netloc
        or "127.0.0.1:8070"
    ).strip()
    scheme = (request.headers.get("x-forwarded-proto") or request.url.scheme or "http").strip()
    report_url = f"{scheme}://{host}/api/server-status"
    if key:
        report_url = f"{report_url}?key={key}"
    return server_status_service.generate_shell_script(report_url, server_name=key or "")
