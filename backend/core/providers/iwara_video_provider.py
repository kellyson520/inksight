"""Iwara public video recommendation provider."""
from __future__ import annotations
import asyncio
from typing import Any
from PIL import Image, ImageDraw
from ..outbound_http import RequestPolicy, outbound_http
from ..recommendation_provider import normalize_recommendation_item, resolve_proxy_url
from .base import register_provider

_DEFAULT_ENDPOINT = "https://api.iwara.tv/videos?limit=10&sort=trending"
_FALLBACK_COVER = "https://images.unsplash.com/photo-1534447677768-be436bb09401?w=800&q=80"


def _local_fallback_image() -> Image.Image:
    image = Image.new("RGB", (600, 340), (230, 235, 240))
    draw = ImageDraw.Draw(image)
    for x in range(0, 600, 30):
        draw.line((x, 0, 600 - x, 340), fill=(200, 210, 220), width=2)
    draw.polygon([(260, 130), (260, 210), (340, 170)], fill=(60, 90, 130), outline=(30, 50, 80))
    draw.text((230, 230), "IWARA VIDEO", fill=(50, 70, 90))
    return image


_FALLBACK = [
    {
        "title": "Iwara 视频推荐",
        "subtitle": "精选公开 3D / MMD",
        "source": "iwara",
        "rank_label": "推荐",
        "cover_url": _FALLBACK_COVER,
        "thumbnail_url": _FALLBACK_COVER,
        "image_data": _local_fallback_image(),
    }
]


def _parse_iwara_items(payload: Any) -> list[dict[str, Any]]:
    raw = payload.get("results", payload.get("data", payload)) if isinstance(payload, dict) else payload
    if not isinstance(raw, list):
        return []
    result = []
    for index, item in enumerate(raw[:10], 1):
        if not isinstance(item, dict):
            continue
        user = item.get("user") if isinstance(item.get("user"), dict) else {}
        file_info = item.get("file") if isinstance(item.get("file"), dict) else {}
        file_id = str(file_info.get("id") or "").strip()
        thumb_val = item.get("thumbnail")
        cover_url = ""
        if file_id:
            try:
                thumb_idx = int(thumb_val) if thumb_val is not None else 0
            except (TypeError, ValueError):
                thumb_idx = 0
            cover_url = f"https://files.iwara.tv/image/large/{file_id}/thumbnail-{thumb_idx:02d}.jpg"
        elif isinstance(thumb_val, str) and thumb_val.startswith("http"):
            cover_url = thumb_val
        elif item.get("thumbnailUrl") and str(item.get("thumbnailUrl")).startswith("http"):
            cover_url = str(item.get("thumbnailUrl"))

        result.append(
            normalize_recommendation_item(
                {
                    "title": item.get("title"),
                    "subtitle": user.get("name") or user.get("username") or item.get("username") or "",
                    "cover_url": cover_url,
                    "thumbnail_url": cover_url,
                    "detail_url": f"https://www.iwara.tv/video/{item.get('id')}" if item.get("id") else "",
                    "rank_label": f"NO.{index}",
                },
                source="iwara",
            )
        )
    return result


@register_provider("iwara_video")
async def generate_iwara_video(mode_def, content_cfg, fallback, **kwargs):
    config = kwargs.get("config") or {}
    override = config.get("mode_overrides", {}).get("IWARA_VIDEO", {})
    if not isinstance(override, dict):
        override = {}
    settings = config.get("mode_settings") or {}
    endpoint = override.get("endpoint") or settings.get("endpoint") or content_cfg.get("endpoint") or _DEFAULT_ENDPOINT
    proxy_url = resolve_proxy_url(config.get("global_proxy_url"), auto_detect=True)

    items = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
        "Referer": "https://www.iwara.tv/",
    }
    try:
        response = await asyncio.to_thread(
            outbound_http.get_json,
            endpoint,
            headers=headers,
            proxy_url=proxy_url,
            policy=RequestPolicy(max_attempts=2, follow_redirects=True),
        )
        items = _parse_iwara_items(response.json())
    except Exception:
        pass

    return {
        "title": "iwara 视频推荐",
        "source": "iwara",
        "items": items or _FALLBACK,
        "layout_style": override.get("layout_style", "cover_card"),
    }
