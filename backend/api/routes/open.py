"""
开放 API 路由 (参考 Dot Quote/0 Open API 规范)
提供灵活的外部调用与 Webhook 推送能力：
- POST /api/open/device/{mac}/text : 向指定设备推送即时图文/提醒/通知
- POST /api/open/device/{mac}/rss : 动态为设备切换或配置 RSS 源
- POST /api/open/preview/render : 开放渲染测试接口
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from core.config_store import get_active_config, save_config
from core.rss_parser import fetch_and_parse_rss, get_rss_item_content

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/open", tags=["open"])


class OpenTextPayload(BaseModel):
    title: Optional[str] = Field(default="", description="卡片标题")
    message: str = Field(..., description="正文内容")
    signature: Optional[str] = Field(default="", description="署名或时间戳")
    icon: Optional[str] = Field(default=None, description="图标或图片 URL")
    link: Optional[str] = Field(default=None, description="跳转链接（备用）")
    refresh_now: Optional[bool] = Field(default=False, description="是否立即通知刷新")


class OpenRssPayload(BaseModel):
    feed_url: str = Field(..., description="RSS/Atom 订阅源地址")
    item_index: Optional[int] = Field(default=0, description="默认展示文章序号")
    show_image: Optional[bool] = Field(default=True, description="是否展示配图")


class OpenDataPayload(BaseModel):
    title: Optional[str] = Field(default=None, description="卡片主标题")
    primary_metric: Optional[str] = Field(default=None, description="核心大字数值 (如 25.4°C / 98%)")
    primary_label: Optional[str] = Field(default=None, description="核心数值说明副标")
    status_tag: Optional[str] = Field(default=None, description="状态标签 (如 优良 / 正常)")
    item_1_value: Optional[str] = Field(default=None, description="指标项 1 数值/文本")
    item_2_value: Optional[str] = Field(default=None, description="指标项 2 数值/文本")
    item_3_value: Optional[str] = Field(default=None, description="指标项 3 数值/文本")
    timestamp: Optional[str] = Field(default=None, description="时间戳 (缺省自动填当前时间)")
    raw_data: Optional[dict[str, Any]] = Field(default=None, description="透传任意结构化键值")


@router.post("/device/{mac}/text")
async def push_device_text(mac: str, payload: OpenTextPayload):
    """
    参考 Dot Quote/0 Open API:
    通过 Webhook 向指定设备推送即时文字内容。
    会自动将其写入该设备的 MEMO 模式首组便签，并设置为待生效内容。
    """
    clean_mac = mac.strip().upper()
    cfg = await get_active_config(clean_mac)
    if not cfg:
        cfg = {"mac": clean_mac}

    mode_overrides = cfg.get("mode_overrides") or {}
    if not isinstance(mode_overrides, dict):
        mode_overrides = {}

    title = payload.title.strip() if payload.title else "实时消息"
    text = payload.message.strip()
    if payload.signature:
        text = f"{text}\n\n— {payload.signature.strip()}"

    mode_overrides["MEMO"] = {
        "memo_title_1": title,
        "memo_text_1": text,
        "memo_title_2": "",
        "memo_text_2": "",
        "memo_title_3": "",
        "memo_text_3": "",
    }
    cfg["mode_overrides"] = mode_overrides

    cfg["current_mode"] = "MEMO"
    await save_config(clean_mac, cfg)

    logger.info("[OpenAPI] Pushed custom text to device %s: %s", clean_mac, title)
    return {
        "code": 0,
        "message": f"Device {clean_mac} text content updated.",
        "data": {
            "mac": clean_mac,
            "mode": "MEMO",
            "title": title,
        }
    }


@router.post("/device/{mac}/rss")
async def set_device_rss(mac: str, payload: OpenRssPayload):
    """
    通过开放接口为设备绑定或即时切换 RSS 订阅源。
    """
    clean_mac = mac.strip().upper()
    cfg = await get_active_config(clean_mac)
    if not cfg:
        cfg = {"mac": clean_mac}

    feed_url = payload.feed_url.strip()
    if not feed_url:
        raise HTTPException(status_code=400, detail="feed_url cannot be empty")

    mode_overrides = cfg.get("mode_overrides") or {}
    if not isinstance(mode_overrides, dict):
        mode_overrides = {}

    mode_overrides["RSS"] = {
        "feed_url": feed_url,
        "item_index": payload.item_index or 0,
        "show_image": bool(payload.show_image),
    }
    cfg["mode_overrides"] = mode_overrides
    cfg["current_mode"] = "RSS"
    await save_config(clean_mac, cfg)

    logger.info("[OpenAPI] Configured RSS feed for device %s: %s", clean_mac, feed_url)
    return {
        "code": 0,
        "message": f"Device {clean_mac} RSS feed configured.",
        "data": {
            "mac": clean_mac,
            "mode": "RSS",
            "feed_url": feed_url,
        }
    }


@router.get("/rss/inspect")
async def inspect_rss(feed_url: str):
    """
    开放测试辅助端点：解析并预览任意 RSS 源的有效性、文章标题、配图与摘要。
    """
    parsed = await fetch_and_parse_rss(feed_url)
    sample = get_rss_item_content(parsed, 0)
    return {
        "feed_title": parsed.get("title"),
        "feed_desc": parsed.get("description"),
        "total_items": len(parsed.get("items", [])),
        "sample_item": sample,
    }


@router.post("/device/{mac}/data")
async def push_device_data(mac: str, payload: OpenDataPayload):
    """
    通用开放 Webhook 数据卡片接收端点：
    允许外部系统（Home Assistant、自建运维监控、个人跑步记录、IoT设备）
    向指定 InkSight 墨水屏推送自定义结构化数据看板。
    """
    clean_mac = mac.strip().upper()
    cfg = await get_active_config(clean_mac)
    if not cfg:
        cfg = {"mac": clean_mac}

    mode_overrides = cfg.get("mode_overrides") or {}
    if not isinstance(mode_overrides, dict):
        mode_overrides = {}

    webhook_data = dict(mode_overrides.get("WEBHOOK") or {})
    
    # 填充字段
    if payload.raw_data and isinstance(payload.raw_data, dict):
        webhook_data.update(payload.raw_data)
    if payload.title is not None:
        webhook_data["title"] = payload.title
    if payload.primary_metric is not None:
        webhook_data["primary_metric"] = payload.primary_metric
    if payload.primary_label is not None:
        webhook_data["primary_label"] = payload.primary_label
    if payload.status_tag is not None:
        webhook_data["status_tag"] = payload.status_tag
    if payload.item_1_value is not None:
        webhook_data["item_1_value"] = payload.item_1_value
    if payload.item_2_value is not None:
        webhook_data["item_2_value"] = payload.item_2_value
    if payload.item_3_value is not None:
        webhook_data["item_3_value"] = payload.item_3_value
    if payload.timestamp is not None:
        webhook_data["timestamp"] = payload.timestamp

    mode_overrides["WEBHOOK"] = webhook_data
    cfg["mode_overrides"] = mode_overrides
    cfg["current_mode"] = "WEBHOOK"
    await save_config(clean_mac, cfg)

    logger.info("[OpenAPI] Pushed custom webhook data to device %s: %s", clean_mac, webhook_data.get("title"))
    return {
        "code": 0,
        "message": f"Device {clean_mac} webhook data updated.",
        "data": {
            "mac": clean_mac,
            "mode": "WEBHOOK",
            "card_title": webhook_data.get("title"),
        }
    }

