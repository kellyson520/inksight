"""
Mihomo (Clash.Meta) 容器与订阅额度 Provider (Mihomo Sub Provider)
为墨水屏提供 Mihomo 容器状态监控与代理订阅流量额度、有效期、剩余天数、节点状态解析。
【规范约束】：严格禁止 Emoji。
"""
from __future__ import annotations

import logging
from typing import Any

from core.mihomo_service import mihomo_service
from .base import register_provider

logger = logging.getLogger(__name__)


@register_provider("mihomo_sub")
async def generate_mihomo_sub(
    mode_def: dict[str, Any],
    content_cfg: dict[str, Any],
    fallback: dict[str, Any],
    **kwargs: Any,
) -> dict[str, Any]:
    config = kwargs.get("config") or {}
    mode_settings = config.get("mode_settings") or {}
    mode_overrides = config.get("mode_overrides") or {}
    override = mode_overrides.get("MIHOMO_SUB") or {}

    sub_url = None
    api_url = None
    api_secret = None
    name = None

    if isinstance(override, dict):
        sub_url = override.get("subscription_url")
        api_url = override.get("api_url")
        api_secret = override.get("api_secret")
        name = override.get("name")
    elif isinstance(mode_settings, dict):
        sub_url = mode_settings.get("subscription_url")
        api_url = mode_settings.get("api_url")
        api_secret = mode_settings.get("api_secret")
        name = mode_settings.get("name")

    if not sub_url and content_cfg.get("subscription_url"):
        sub_url = str(content_cfg["subscription_url"])
    if not api_url and content_cfg.get("api_url"):
        api_url = str(content_cfg["api_url"])
    if not api_secret and content_cfg.get("api_secret"):
        api_secret = str(content_cfg["api_secret"])
    if not name and content_cfg.get("name"):
        name = str(content_cfg["name"])

    try:
        data = await mihomo_service.get_dashboard_data(
            sub_url=sub_url,
            api_url=api_url,
            api_secret=api_secret,
            name=name,
        )
        if data:
            return data
    except Exception as exc:
        logger.warning("[MihomoSubProvider] Failed to get mihomo dashboard data: %s", exc)

    return dict(fallback)
