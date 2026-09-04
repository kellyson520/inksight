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

    # 提取多平台或单平台配置
    platforms_raw = None
    if isinstance(override, dict):
        platforms_raw = override.get("platforms") or override.get("platform")
    if not platforms_raw and isinstance(mode_settings, dict):
        platforms_raw = mode_settings.get("platforms") or mode_settings.get("platform")
    if not platforms_raw:
        platforms_raw = content_cfg.get("platforms") or content_cfg.get("platform") or "zhihu"

    try:
        data = await hotlist_service.get_multi_hotlist(platforms_raw)
        if data:
            return data
    except Exception as exc:
        logger.warning("[HotlistProvider] Failed to get hotlist for %s: %s", platforms_raw, exc)

    # 异常兜底
    return await hotlist_service.get_multi_hotlist("zhihu")
