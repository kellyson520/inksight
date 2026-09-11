"""Public Pornhub recommendation adapter; no login or access-control bypass."""
from __future__ import annotations
import asyncio
from typing import Any
import httpx
from PIL import Image, ImageDraw
from ..outbound_http import RequestPolicy, outbound_http
from ..recommendation_provider import normalize_recommendation_item, resolve_proxy_url
from .base import register_provider

_DEFAULT_ENDPOINT = "https://www.pornhub.com/webmasters/search?thumbsize=large"
_FALLBACK_COVER = "https://images.unsplash.com/photo-1518709268805-4e9042af9f23?w=800&q=80"


def _local_fallback_image() -> Image.Image:
    image = Image.new("RGB", (600, 340), (20, 20, 25))
    draw = ImageDraw.Draw(image)
    draw.rectangle([200, 130, 400, 210], fill=(255, 153, 0))
    draw.text((230, 155), "PORNHUB", fill=(0, 0, 0))
    return image


_FALLBACK = [
    {
        "title": "P站公开视频推荐",
        "subtitle": "精选公开热门",
        "source": "P站",
        "rank_label": "推荐",
        "cover_url": _FALLBACK_COVER,
        "thumbnail_url": _FALLBACK_COVER,
        "image_data": _local_fallback_image(),
    }
]


def _parse_porn_items(payload: Any) -> list[dict[str, Any]]:
    raw = payload.get("videos", payload.get("data", payload)) if isinstance(payload, dict) else payload
    if not isinstance(raw, list):
        return []
    result = []
    for index, item in enumerate(raw[:10], 1):
        if not isinstance(item, dict):
            continue
        thumbs = item.get("thumbs") or []
        thumb_url = item.get("default_thumb") or (thumbs[0].get("src") if thumbs and isinstance(thumbs[0], dict) else "")
        result.append(
            normalize_recommendation_item(
                {
                    "title": item.get("title"),
                    "subtitle": item.get("username") or item.get("uploader"),
                    "thumbnail": thumb_url or item.get("thumbnail") or item.get("thumb"),
                    "detail_url": item.get("url"),
                    "rank_label": f"NO.{index}",
                },
                source="P站",
            )
        )
    return result


@register_provider("porn_video")
async def generate_porn_video(mode_def, content_cfg, fallback, **kwargs):
    config = kwargs.get("config") or {}
    override = config.get("mode_overrides", {}).get("PORN_VIDEO", {})
    if not isinstance(override, dict):
        override = {}
    settings = config.get("mode_settings") or {}
    endpoint = override.get("endpoint") or settings.get("endpoint") or content_cfg.get("endpoint") or _DEFAULT_ENDPOINT
    proxy_url = resolve_proxy_url(config.get("global_proxy_url"))
    items = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
    }
    try:
        policy = RequestPolicy(
            timeout=httpx.Timeout(connect=2.5, read=5.0, write=3.0, pool=2.5),
            max_attempts=1 if not proxy_url else 2,
            follow_redirects=True,
        )
        response = await asyncio.to_thread(
            outbound_http.get_json,
            endpoint,
            headers=headers,
            proxy_url=proxy_url,
            policy=policy,
        )
        items = _parse_porn_items(response.json())
    except Exception:
        pass
    return {
        "title": "P站视频推荐",
        "source": "P站",
        "items": items or _FALLBACK,
        "layout_style": override.get("layout_style", "ranking"),
    }
