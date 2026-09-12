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


def _local_fallback_image(title: str = "Iwara 推荐视频", author: str = "Creator", rank_label: str = "NO.1") -> Image.Image:
    image = Image.new("RGB", (640, 360), (245, 247, 250))
    draw = ImageDraw.Draw(image)
    # 外框
    draw.rounded_rectangle([4, 4, 635, 355], radius=16, outline=(170, 180, 195), width=2)
    # 顶部品牌条
    draw.rounded_rectangle([24, 20, 160, 62], radius=8, fill=(30, 45, 65))
    draw.text((36, 28), "IWARA", fill=(255, 255, 255))
    if rank_label:
        draw.rounded_rectangle([530, 20, 616, 60], radius=8, fill=(230, 235, 245), outline=(180, 190, 205), width=1)
        draw.text((544, 28), rank_label, fill=(25, 35, 50))
    # 中心播放图标
    cx, cy = 320, 174
    draw.ellipse([cx - 48, cy - 48, cx + 48, cy + 48], fill=(35, 55, 80), outline=(80, 130, 190), width=3)
    draw.polygon([(cx - 12, cy - 20), (cx - 12, cy + 20), (cx + 22, cy)], fill=(255, 255, 255))
    # 底部标签
    draw.rounded_rectangle([24, 302, 220, 340], radius=6, fill=(230, 235, 245), outline=(180, 190, 205), width=1)
    draw.text((34, 310), f"▶ 3D / MMD · {author[:10]}", fill=(30, 45, 65))
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
        "fallback_image": _local_fallback_image(),
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

        title = item.get("title") or f"视频 #{index}"
        author = user.get("name") or user.get("username") or item.get("username") or ""
        rank_str = f"NO.{index}"
        local_cover = _local_fallback_image(title=title, author=author, rank_label=rank_str)

        result.append(
            normalize_recommendation_item(
                {
                    "title": title,
                    "subtitle": author,
                    "cover_url": cover_url,
                    "thumbnail_url": cover_url,
                    "detail_url": f"https://www.iwara.tv/video/{item.get('id')}" if item.get("id") else "",
                    "rank_label": rank_str,
                    "fallback_image": local_cover,
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
