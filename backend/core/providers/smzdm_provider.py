"""
什么值得买好价排行 Provider (SMZDM Provider)
为墨水屏提供什么值得买热门好价、数码榜与白菜价榜单数据。
【规范约束】：严格禁止 Emoji。
"""
from __future__ import annotations

import logging
from typing import Any

from core.smzdm_service import smzdm_service
from .base import register_provider

logger = logging.getLogger(__name__)


@register_provider("smzdm")
async def generate_smzdm(
    mode_def: dict[str, Any],
    content_cfg: dict[str, Any],
    fallback: dict[str, Any],
    **kwargs: Any,
) -> dict[str, Any]:
    config = kwargs.get("config") or {}
    mode_settings = config.get("mode_settings") or {}
    mode_overrides = config.get("mode_overrides") or {}
    override = mode_overrides.get("SMZDM") or {}

    category = "ALL"
    if isinstance(override, dict) and override.get("category"):
        category = str(override["category"])
    elif isinstance(mode_settings, dict) and mode_settings.get("category"):
        category = str(mode_settings["category"])
    elif content_cfg.get("category"):
        category = str(content_cfg["category"])

    device_mac = kwargs.get("device_mac")
    date_ctx = kwargs.get("date_ctx") or {}
    date_str = date_ctx.get("date_str", "")
    seed = f"{device_mac}_{date_str}_{category}" if device_mac else None

    try:
        data = smzdm_service.get_ranking(
            category=category,
            count=5,
            seed=seed,
        )
        if data:
            return data
    except Exception as exc:
        logger.warning("[SmzdmProvider] Failed to get SMZDM ranking: %s", exc)

    return dict(fallback)
