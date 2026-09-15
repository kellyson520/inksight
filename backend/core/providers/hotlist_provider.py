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
    mode_id = str(mode_def.get("mode_id") or "HOTLIST").upper()
    override = mode_overrides.get(mode_id) or {}

    _DEFAULT_PLATFORMS: dict[str, Any] = {
        "WEIBO": "weibo",
        "ZHIHU": "zhihu",
        "BILIBILI": "bilibili",
        "BAIDU": "baidu",
        "DOUYIN": "douyin",
        "NETEASE": "netease",
        "WECHAT_HOT": "wechat",
        "GITHUB_TRENDING": "github",
        "TIEBA": "tieba",
        "TECH_NEWS": ["36kr", "ithome", "sspai", "github"],
    }

    # 提取排版样式 (各模式可自由选择 dense_grid / cover_card / editorial / classic)
    style = "dense_grid"
    if isinstance(override, dict) and override.get("style"):
        style = str(override["style"])
    elif isinstance(mode_settings, dict) and mode_settings.get("style"):
        style = str(mode_settings["style"])
    elif content_cfg.get("style"):
        style = str(content_cfg["style"])

    # 平台源隔离：独立拆分模式严格锁定其自身原生平台，绝对禁止被外部 override 或聚合热点配置污染
    if mode_id in _DEFAULT_PLATFORMS:
        platforms_raw = _DEFAULT_PLATFORMS[mode_id]
    else:
        # 仅针对通用多源聚合热点 HOTLIST 模式读取用户勾选的多平台配置
        platforms_raw = None
        if isinstance(override, dict):
            platforms_raw = override.get("platforms") or override.get("platform")
        if not platforms_raw and isinstance(mode_settings, dict):
            platforms_raw = mode_settings.get("platforms") or mode_settings.get("platform")
        if not platforms_raw:
            platforms_raw = (
                content_cfg.get("platform")
                or content_cfg.get("platforms")
                or ["zhihu", "weibo", "bilibili"]
            )

    _STYLE_BADGES = {
        "dense_grid": "双列看板",
        "cover_card": "图文精选",
        "editorial": "深度焦点",
        "classic": "单列排行",
    }
    style_badge = _STYLE_BADGES.get(style, "热点精选")

    try:
        data = await hotlist_service.get_multi_hotlist(platforms_raw, limit=8)
        if data:
            data["style"] = style
            data["style_badge"] = style_badge
            return data
    except Exception as exc:
        logger.warning("[HotlistProvider] Failed to get hotlist for %s (%s): %s", mode_id, platforms_raw, exc)

    # 异常兜底
    data = await hotlist_service.get_multi_hotlist(_DEFAULT_PLATFORMS.get(mode_id, "zhihu"), limit=8)
    data["style"] = style
    data["style_badge"] = style_badge
    return data
