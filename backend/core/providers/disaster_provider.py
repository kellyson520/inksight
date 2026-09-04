"""
自然灾害预警 Provider (Disaster Alert)
接入国家标准气象灾害预警引擎与防灾避险知识库。
"""
from __future__ import annotations

import logging
import time
from typing import Any

from core.disaster_service import (
    check_device_disaster_alert,
    normalize_warning_level,
    _generate_default_advice,
    _map_hazard_to_key,
)
from .base import register_provider

logger = logging.getLogger(__name__)


@register_provider("disaster_alert")
async def generate_disaster_alert(
    mode_def: dict[str, Any],
    content_cfg: dict[str, Any],
    fallback: dict[str, Any],
    **kwargs: Any,
) -> dict[str, Any]:
    config = kwargs.get("config") or {}
    mode_overrides = config.get("mode_overrides") or {}
    override = mode_overrides.get("DISASTER_ALERT") or {}
    mac = kwargs.get("mac") or ""

    # 1. 优先检查当前设备绑定的真实或模拟预警
    try:
        active = await check_device_disaster_alert(mac, config)
        if active:
            lvl = active.get("level", "红色")
            score, meta = normalize_warning_level(lvl)
            hazard_key = active.get("hazard_key") or _map_hazard_to_key(active.get("type_name", ""))
            advices = active.get("advice") or _generate_default_advice(hazard_key)
            clean_lvl = lvl.replace("预警", "").strip()
            return {
                "level": clean_lvl,
                "type_name": active.get("type_name", "气象灾害"),
                "hazard_key": hazard_key,
                "title": active.get("title", f"【{active.get('type_name', '气象灾害')}{clean_lvl}预警】"),
                "sender": active.get("sender", "国家气象局"),
                "pub_time": active.get("pub_time", time.strftime("%H:%M")),
                "text": active.get("text", "预警信号生效中，请做好防范。"),
                "advice": advices,
                "theme_color": meta.get("eink_color", "black"),
            }
    except Exception as exc:
        logger.warning("[DisasterProvider] Failed to check active alert: %s", exc)

    # 2. 无活跃预警时，按用户在预览或模式设置中选取的参数渲染体验
    level = str(override.get("level") or content_cfg.get("level") or "红色")
    hazard = str(override.get("hazard") or content_cfg.get("hazard") or "暴雨")
    score, meta = normalize_warning_level(level)
    hazard_key = _map_hazard_to_key(hazard)
    advices = _generate_default_advice(hazard_key)

    sender = str(override.get("sender") or "国家气象防灾指挥中心")
    pub_time = str(override.get("pub_time") or time.strftime("%H:%M"))
    text = str(override.get("text") or f"气象台发布{hazard}{level}预警信号，请各单位及居民全面做好防灾应急与避险工作。")

    clean_level = level.replace("预警", "").strip()
    return {
        "level": clean_level,
        "type_name": hazard,
        "hazard_key": hazard_key,
        "title": f"【{hazard}{clean_level}预警】",
        "sender": sender,
        "pub_time": pub_time,
        "text": text,
        "advice": advices,
        "theme_color": meta.get("eink_color", "black"),
    }
