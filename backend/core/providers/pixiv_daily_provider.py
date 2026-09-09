"""Pixiv daily illustration provider."""
from __future__ import annotations
import asyncio
from io import BytesIO
from typing import Any
from PIL import Image, ImageDraw
from ..outbound_http import RequestPolicy, outbound_http
from ..recommendation_provider import normalize_recommendation_item, resolve_proxy_url
from .base import register_provider

_FALLBACK_IMAGE = "https://images.unsplash.com/photo-1579783902614-a3fb3927b6a5?w=1200&q=80"
_FALLBACK_ITEM = {"title": "Pixiv 每日一图", "subtitle": "每日精选插画", "source": "Pixiv", "rank_label": "DAILY", "image": _FALLBACK_IMAGE, "cover_url": _FALLBACK_IMAGE, "thumbnail_url": _FALLBACK_IMAGE}
def _local_fallback_image() -> Image.Image:
    image = Image.new("RGB", (800, 500), (232, 226, 214))
    draw = ImageDraw.Draw(image)
    for x in range(0, 800, 40):
        draw.line((x, 0, 800 - x, 500), fill=(190, 180, 160), width=3)
    draw.ellipse((300, 90, 500, 290), fill=(120, 95, 145), outline=(70, 55, 90), width=8)
    draw.text((275, 360), "PIXIV DAILY", fill=(45, 38, 50))
    return image


_FALLBACK = {"title": "Pixiv 每日一图", "subtitle": "每日精选插画", "source": "Pixiv", "rank_label": "DAILY", "items": [{**_FALLBACK_ITEM, "image_data": _local_fallback_image()}]}


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
    if not item:
        return {**_FALLBACK, "layout_style": override.get("layout_style", "cover_card")}
    selected = dict(item)
    if "items" not in selected:
        selected["items"] = [selected]
    return {**_FALLBACK, **selected, "layout_style": override.get("layout_style", "cover_card")}
