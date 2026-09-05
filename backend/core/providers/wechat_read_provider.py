"""
微信读书推荐 Provider (WeChat Read Provider)
为墨水屏提供微信读书精选书籍推荐，含书名、作者、评分、推荐理由与封面。
【规范约束】：严禁 Emoji。
"""
from __future__ import annotations

import logging
from typing import Any

from core.wechat_read_service import wechat_read_service
from .base import register_provider

logger = logging.getLogger(__name__)


@register_provider("wechat_read")
async def generate_wechat_read(
    mode_def: dict[str, Any],
    content_cfg: dict[str, Any],
    fallback: dict[str, Any],
    **kwargs: Any,
) -> dict[str, Any]:
    config = kwargs.get("config") or {}
    mode_settings = config.get("mode_settings") or {}
    mode_overrides = config.get("mode_overrides") or {}
    override = mode_overrides.get("WECHAT_READ") or {}

    category = "ALL"
    book_id = None
    if isinstance(override, dict):
        if override.get("category"):
            category = str(override["category"])
        if override.get("book_id"):
            book_id = str(override["book_id"])
    elif isinstance(mode_settings, dict):
        if mode_settings.get("category"):
            category = str(mode_settings["category"])
        if mode_settings.get("book_id"):
            book_id = str(mode_settings["book_id"])
    elif content_cfg.get("category"):
        category = str(content_cfg["category"])

    device_mac = kwargs.get("device_mac")
    date_ctx = kwargs.get("date_ctx") or {}
    date_str = date_ctx.get("date_str", "")
    seed = f"{device_mac}_{date_str}_{category}" if device_mac else None

    try:
        data = wechat_read_service.get_recommended_book(
            category=category,
            book_id=book_id,
            seed=seed,
        )
        if data:
            return data
    except Exception as exc:
        logger.warning("[WeChatReadProvider] Failed to get book recommendation: %s", exc)

    res = dict(fallback)
    return res
