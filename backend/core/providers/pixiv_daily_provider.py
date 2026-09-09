"""Pixiv daily illustration provider."""
from __future__ import annotations
import asyncio
from typing import Any
from ..outbound_http import RequestPolicy, outbound_http
from ..recommendation_provider import normalize_recommendation_item, resolve_proxy_url
from .base import register_provider

_FALLBACK = {"title": "Pixiv 每日一图", "subtitle": "每日精选插画", "source": "Pixiv", "rank_label": "DAILY"}


def _parse_pixiv_item(payload: Any) -> dict[str, Any]:
    item = payload.get("illust", payload) if isinstance(payload, dict) else {}
    user = item.get("user") if isinstance(item, dict) else {}
    user = user if isinstance(user, dict) else {}
    return normalize_recommendation_item({
        "title": item.get("title"), "subtitle": user.get("name") or item.get("user_name"),
        "image": item.get("image") or item.get("image_url") or item.get("url"),
        "thumbnail": item.get("thumbnail") or item.get("thumbnail_url"),
        "detail_url": item.get("detail_url") or item.get("url"),
        "description": item.get("description"), "rank_label": "DAILY",
    }, source="Pixiv")


@register_provider("pixiv_daily")
async def generate_pixiv_daily(mode_def, content_cfg, fallback, **kwargs):
    config = kwargs.get("config") or {}; override = config.get("mode_overrides", {}).get("PIXIV_DAILY", {})
    if not isinstance(override, dict): override = {}
    settings = config.get("mode_settings") or {}
    endpoint = override.get("endpoint") or settings.get("endpoint") or content_cfg.get("endpoint")
    item = {}
    if endpoint:
        try:
            response = await asyncio.to_thread(outbound_http.get_json, endpoint, proxy_url=resolve_proxy_url(config.get("global_proxy_url")), policy=RequestPolicy(max_attempts=1, follow_redirects=True))
            item = _parse_pixiv_item(response.json())
        except Exception: pass
    return {**_FALLBACK, **(item or fallback or {}), "layout_style": override.get("layout_style", "cover_card")}
