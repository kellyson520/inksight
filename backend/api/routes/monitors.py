"""
网页变动与事件监控 API 路由 (Monitor & Event Notification Routes)
提供监控目标的增删改查、即时变动检测触发与突发事件推送接口。
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import os
import time
from pathlib import Path
from typing import Any
from fastapi import APIRouter, Cookie, Depends, Header, HTTPException, Request
from pydantic import BaseModel, Field

from core.monitor_service import monitor_service
from api.shared import require_membership_access
from core.auth import require_admin, validate_mac_param
from core.monitor_nonce_store import MonitorNonceStore

logger = logging.getLogger(__name__)
_MONITOR_SIGNATURE_WINDOW_SECONDS = 300
_MONITOR_NONCE_STORE = MonitorNonceStore(
    Path(__file__).resolve().parents[2] / "data" / "monitor_nonces.sqlite"
)

router = APIRouter(prefix="/monitors", tags=["monitors"])


class TargetCreateSchema(BaseModel):
    id: str | None = None
    name: str = Field(..., description="监控项名称")
    url: str = Field(..., description="监控目标网页URL")
    enabled: bool = True
    check_interval: int = Field(300, description="检查间隔秒数")
    max_presentations: int = Field(2, description="变动后插播呈现次数上限")
    target_mac: str = Field("*", description="关联设备MAC或通配符*")


class EventPushSchema(BaseModel):
    site_name: str = Field(..., description="站点/服务名称")
    url: str = Field("", description="变动相关链接")
    title: str = Field("检测到关键事件更新", description="通报标题")
    prev_snippet: str = Field("", description="前置摘要或状态")
    new_snippet: str = Field(..., description="新内容或报警详情")
    max_presentations: int = Field(2, description="插播呈现次数")
    target_mac: str = Field("*", description="目标设备MAC")


@router.get("")
async def list_targets(_: None = Depends(require_admin)) -> dict[str, Any]:
    """列出当前所有监控目标。"""
    targets = monitor_service.list_targets()
    return {"success": True, "targets": targets}


@router.post("")
async def create_or_update_target(payload: TargetCreateSchema, _: None = Depends(require_admin)) -> dict[str, Any]:
    """创建或更新监控目标。"""
    target = monitor_service.add_target(payload.model_dump())
    return {"success": True, "target": target}


@router.delete("/{target_id}")
async def delete_target(target_id: str, _: None = Depends(require_admin)) -> dict[str, Any]:
    """删除指定监控目标。"""
    deleted = monitor_service.delete_target(target_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Target not found")
    return {"success": True, "target_id": target_id}


@router.post("/check")
async def trigger_check(_: None = Depends(require_admin)) -> dict[str, Any]:
    """即时触发所有启用的监控项检测，返回触发的通知事件。"""
    targets = monitor_service.list_targets()
    triggered_notices = []
    for t in targets:
        if t.get("enabled", True):
            notice = await monitor_service.check_target(t)
            if notice:
                triggered_notices.append(notice)
    return {
        "success": True,
        "checked_count": len(targets),
        "triggered_count": len(triggered_notices),
        "notices": triggered_notices,
    }


@router.get("/notices")
async def list_notices(active_only: bool = False, _: None = Depends(require_admin)) -> dict[str, Any]:
    """获取变动通报列表。"""
    notices = monitor_service.list_notices(active_only=active_only)
    return {"success": True, "notices": notices}


@router.post("/notices/clear")
async def clear_notices(_: None = Depends(require_admin)) -> dict[str, Any]:
    """清空所有历史与活跃变动通报。"""
    monitor_service.clear_notices()
    return {"success": True, "message": "All notices cleared"}


@router.post("/events")
async def push_event(
    payload: EventPushSchema,
    request: Request,
    ink_session: str | None = Cookie(default=None),
    x_device_token: str | None = Header(default=None, alias="X-Device-Token"),
    x_monitor_timestamp: str | None = Header(default=None, alias="X-Monitor-Timestamp"),
    x_monitor_nonce: str | None = Header(default=None, alias="X-Monitor-Nonce"),
    x_monitor_signature: str | None = Header(default=None, alias="X-Monitor-Signature"),
) -> dict[str, Any]:
    """外部 Webhook 或监控告警推送接口，直接触发插播通报卡片。"""
    target_mac = payload.target_mac
    if target_mac == "*":
        secret = os.environ.get("MONITOR_WEBHOOK_SECRET", "")
        try:
            timestamp = int(x_monitor_timestamp or "")
        except ValueError:
            timestamp = 0
        now = int(time.time())
        if not x_monitor_nonce or abs(now - timestamp) > _MONITOR_SIGNATURE_WINDOW_SECONDS:
            raise HTTPException(status_code=403, detail="signed_monitor_webhook_required")
        signed_body = f"{timestamp}.{x_monitor_nonce}.{payload.model_dump_json()}".encode()
        expected = hmac.new(secret.encode(), signed_body, hashlib.sha256).hexdigest() if secret else ""
        if not x_monitor_signature or not expected or not hmac.compare_digest(x_monitor_signature, expected):
            raise HTTPException(status_code=403, detail="signed_monitor_webhook_required")
        try:
            consumed = await _MONITOR_NONCE_STORE.consume(
                x_monitor_nonce,
                expires_at=timestamp + _MONITOR_SIGNATURE_WINDOW_SECONDS,
            )
        except Exception as exc:
            logger.error("[Monitor] nonce store unavailable: %s", exc)
            raise HTTPException(status_code=503, detail="replay_protection_unavailable") from exc
        if not consumed:
            raise HTTPException(status_code=403, detail="replayed_monitor_webhook")
    else:
        await require_membership_access(request, target_mac, ink_session, owner_only=True)
    notice = monitor_service.create_change_notice(
        target_id="webhook_event",
        site_name=payload.site_name,
        url=payload.url,
        title=payload.title,
        prev_snippet=payload.prev_snippet,
        new_snippet=payload.new_snippet,
        max_presentations=payload.max_presentations,
        target_mac=target_mac,
    )
    return {"success": True, "notice": notice}
