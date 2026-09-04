"""
通用开放 Webhook 数据卡片 Provider
允许第三方系统（Home Assistant、自建监控、IoT传感器、iOS快捷指令等）
向指定设备投递结构化键值数据并在墨水屏上以仪表盘卡片的形式展示。
"""
from __future__ import annotations

import logging
import time
from typing import Any

from .base import register_provider

logger = logging.getLogger(__name__)

# 预置高质量默认仪表盘数据（如智能家居环境看板）
_DEFAULT_DASHBOARD = {
    "title": "家庭环境与能耗",
    "primary_metric": "23.6°C",
    "primary_label": "室内舒适温度",
    "status_tag": "优良",
    "item_1_label": "空气湿度",
    "item_1_value": "48% 舒适",
    "item_2_label": "PM2.5 质量",
    "item_2_value": "12 μg/m³",
    "item_3_label": "今日用电量",
    "item_3_value": "4.2 kWh",
    "timestamp": time.strftime("%H:%M"),
}


@register_provider("webhook")
async def generate_webhook_data(
    mode_def: dict[str, Any],
    content_cfg: dict[str, Any],
    fallback: dict[str, Any],
    **kwargs: Any,
) -> dict[str, Any]:
    config = kwargs.get("config") or {}
    mode_settings = config.get("mode_settings") or {}
    mode_overrides = config.get("mode_overrides") or {}
    override = mode_overrides.get("WEBHOOK") or {}

    res = dict(fallback if fallback else _DEFAULT_DASHBOARD)

    # 优先应用 mode_settings
    if isinstance(mode_settings, dict):
        for k, v in mode_settings.items():
            if v is not None and str(v).strip():
                res[k] = str(v).strip()

    # 最高优先级：mode_overrides（例如刚刚通过 Webhook 推送的数据或在 preview 调试的数据）
    if isinstance(override, dict):
        for k, v in override.items():
            if v is not None and str(v).strip():
                res[k] = str(v).strip()

    if "timestamp" not in res or not res["timestamp"]:
        res["timestamp"] = time.strftime("%H:%M")

    return res
