"""
RSS / Atom 订阅源模块
"""
from __future__ import annotations

import logging
from typing import Any

from ..rss_parser import fetch_and_parse_rss, get_rss_item_content
from .base import register_provider

logger = logging.getLogger(__name__)


@register_provider("rss")
async def generate_rss(
    mode_def: dict[str, Any],
    content_cfg: dict[str, Any],
    fallback: dict[str, Any],
    **kwargs: Any,
) -> dict[str, Any]:
    config = kwargs.get("config") or {}
    mode_settings = config.get("mode_settings") or {}
    mode_overrides = config.get("mode_overrides") or {}
    rss_override = mode_overrides.get("RSS") or {}

    feed_url = ""
    item_index = 0
    show_image = True

    # 优先级：mode_overrides > mode_settings > content_cfg > 默认测试源
    if isinstance(rss_override, dict):
        feed_url = rss_override.get("feed_url") or rss_override.get("url") or ""
        if "item_index" in rss_override:
            try:
                item_index = int(rss_override["item_index"])
            except (ValueError, TypeError):
                pass
        if "show_image" in rss_override:
            show_image = bool(rss_override["show_image"])

    if not feed_url and isinstance(mode_settings, dict):
        feed_url = mode_settings.get("feed_url") or mode_settings.get("url") or ""
        if "item_index" in mode_settings:
            try:
                item_index = int(mode_settings["item_index"])
            except (ValueError, TypeError):
                pass
        if "show_image" in mode_settings:
            show_image = bool(mode_settings["show_image"])

    if not feed_url:
        feed_url = content_cfg.get("feed_url") or "https://kellson.dpdns.org:81/playno1/av"

    parsed = await fetch_and_parse_rss(feed_url)
    content_item = get_rss_item_content(parsed, index=item_index)
    if not show_image:
        content_item["image_url"] = ""
        content_item["has_image"] = False
    return content_item
