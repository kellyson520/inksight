"""
全网热榜聚合 Provider (Hotlist)
下沉委托至核心基础设施 HotlistService，保持架构清晰、无冗余网络逻辑。
"""
from __future__ import annotations

import logging
from typing import Any

from core.hotlist_service import hotlist_service
from .base import register_provider

logger = logging.getLogger(__name__)


@register_provider("hotlist")
async def generate_hotlist(
    mode_def: dict[str, Any],
    content_cfg: dict[str, Any],
    fallback: dict[str, Any],
    **kwargs: Any,
) -> dict[str, Any]:
    config = kwargs.get("config") or {}
    mode_settings = config.get("mode_settings") or {}
    mode_overrides = config.get("mode_overrides") or {}
    override = mode_overrides.get("HOTLIST") or {}

    platform = "zhihu"
    if isinstance(override, dict) and override.get("platform"):
        platform = str(override["platform"])
    elif isinstance(mode_settings, dict) and mode_settings.get("platform"):
        platform = str(mode_settings["platform"])
    elif content_cfg.get("platform"):
        platform = str(content_cfg["platform"])

    # 统一通过下沉的 hotlist_service 基础设施获取
    try:
        data = await hotlist_service.get_hotlist(platform)
        if data:
            return data
    except Exception as exc:
        logger.warning("[HotlistProvider] Failed to get hotlist for %s: %s", platform, exc)

    # 异常兜底
    clean_plat = hotlist_service.normalize_platform(platform)
    return await hotlist_service.get_hotlist(clean_plat)
