from fastapi import APIRouter, Depends, Header, HTTPException, Query
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from core.push_service import push_dispatcher
from core.auth import require_admin, require_user

router = APIRouter(prefix="/notifications", tags=["notifications"])


class DeviceAlertPushRequest(BaseModel):
    mac: str = Field(..., description="目标墨水屏 MAC 地址")
    sender: str = Field(default="ADMIN", description="告警发送人")
    message: str = Field(..., description="告警正文")
    level: str = Field(default="info", description="告警级别: info/warning/critical")
    ttl_seconds: int = Field(default=300, description="在设备队列中保留的秒数")


class BarkPushRequest(BaseModel):
    bark_key: str = Field(..., description="iOS Bark Key")
    title: str = Field(..., description="通知标题")
    body: str = Field(..., description="通知正文")
    group: str = Field(default="InkSight", description="Bark 分组")
    url: Optional[str] = Field(default=None, description="跳转链接")


class WeChatWebhookPushRequest(BaseModel):
    webhook_url: str = Field(..., description="企业微信群机器人 Webhook URL")
    title: str = Field(..., description="通知标题")
    content: str = Field(..., description="Markdown 内容")


class BroadcastAlertRequest(BaseModel):
    title: str = Field(..., description="全网广播通告标题")
    message: str = Field(..., description="全网广播正文")
    level: str = Field(default="warning", description="级别")
    target_macs: Optional[List[str]] = Field(default=None, description="指定设备列表，留空为广播")


@router.post("/device-alert")
async def send_device_alert(body: DeviceAlertPushRequest, _: Any = Depends(require_user)):
    """向指定墨水屏发送 Focus Alert 实时弹窗提醒。"""
    ok = await push_dispatcher.push_to_device(
        mac=body.mac,
        sender=body.sender,
        message=body.message,
        level=body.level,
        ttl_seconds=body.ttl_seconds,
    )
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to enqueue device alert")
    return {"ok": True, "mac": body.mac}


@router.post("/bark")
async def send_bark_notification(body: BarkPushRequest, _: Any = Depends(require_user)):
    """向 iOS Bark 客户端发送推送。"""
    ok = await push_dispatcher.push_to_bark(
        bark_key=body.bark_key,
        title=body.title,
        body=body.body,
        group=body.group,
        url=body.url,
    )
    return {"ok": ok}


@router.post("/wechat-webhook")
async def send_wechat_webhook(body: WeChatWebhookPushRequest, _: Any = Depends(require_user)):
    """向企业微信群机器人发送 Markdown 消息。"""
    ok = await push_dispatcher.push_to_wechat_webhook(
        webhook_url=body.webhook_url,
        title=body.title,
        content=body.content,
    )
    return {"ok": ok}


@router.post("/broadcast")
async def broadcast_device_alert(body: BroadcastAlertRequest, _: Any = Depends(require_admin)):
    """管理员向多台或全网设备广播通告。"""
    res = await push_dispatcher.broadcast_alert(
        title=body.title,
        message=body.message,
        level=body.level,
        target_macs=body.target_macs,
    )
    return {"ok": True, "result": res}


@router.get("/logs")
async def get_notification_logs(_: Any = Depends(require_admin)):
    """获取最近推送分发日志。"""
    return {"ok": True, "logs": push_dispatcher.get_recent_logs()}
