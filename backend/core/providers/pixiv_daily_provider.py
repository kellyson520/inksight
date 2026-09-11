"""Pixiv daily illustration provider."""
from __future__ import annotations
import asyncio
from io import BytesIO
from typing import Any
from PIL import Image, ImageDraw
import httpx
from ..outbound_http import RequestPolicy, outbound_http

_PRIMARY_ENDPOINT = "https://www.pixiv.net/ranking.php?mode=daily&content=illust&format=json"
_MIRROR_ENDPOINT = "https://api.lolicon.app/setu/v2?r18=0&num=1"
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


def _parse_pixiv_items(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    # 1. Pixiv ranking.php format: {"contents": [{...}, ...]}
    contents = payload.get("contents")
    if isinstance(contents, list) and contents:
        res = []
        for c in contents[:10]:
            if not isinstance(c, dict):
                continue
            title = str(c.get("title") or "Pixiv 推荐")
            author = str(c.get("user_name") or c.get("author") or "")
            url = str(c.get("url") or "")
            # ranking.php url is square thumbnail e.g. .../c/240x480/.../123_p0_square1200.jpg
            # convert to master or original mirror for crisp display
            img_url = url
            if "i.pximg.net" in url:
                img_url = url.replace("i.pximg.net", "i.pixiv.re")
            pid = c.get("illust_id")
            res.append(normalize_recommendation_item({
                "title": title,
                "subtitle": author,
                "image": img_url,
                "thumbnail": img_url,
                "detail_url": f"https://www.pixiv.net/artworks/{pid}" if pid else "",
                "rank_label": f"NO.{c.get('rank', 1)}",
            }, source="Pixiv"))
        return res

    # 2. Lolicon API format: {"data": [{"pid": ..., "title": ..., "urls": {"original": ...}}]}
    data = payload.get("data")
    if isinstance(data, list) and data:
        res = []
        for item in data[:10]:
            if not isinstance(item, dict):
                continue
            urls = item.get("urls") if isinstance(item.get("urls"), dict) else {}
            orig = str(urls.get("original") or urls.get("regular") or "")
            reg = str(urls.get("regular") or urls.get("small") or orig)
            pid = item.get("pid")
            res.append(normalize_recommendation_item({
                "title": str(item.get("title") or "Pixiv 推荐"),
                "subtitle": str(item.get("author") or ""),
                "image": orig,
                "thumbnail": reg,
                "detail_url": f"https://www.pixiv.net/artworks/{pid}" if pid else "",
                "rank_label": "DAILY",
            }, source="Pixiv"))
        return res

    # 3. Legacy body.illust format
    body = payload.get("body") if isinstance(payload, dict) else None
    raw = body.get("illust") if isinstance(body, dict) else None
    if isinstance(raw, list):
        return [_parse_pixiv_item(item) for item in raw if isinstance(item, dict)]

    item = _parse_pixiv_item(payload)
    return [item] if item.get("title") != "未命名推荐" or item.get("cover_url") else []


def _parse_pixiv_item(payload: Any) -> dict[str, Any]:
    item = payload.get("illust", payload) if isinstance(payload, dict) else {}
    user = item.get("user") if isinstance(item, dict) else {}
    user = user if isinstance(user, dict) else {}
    urls = item.get("urls") if isinstance(item.get("urls"), dict) else {}
    original = urls.get("original") or urls.get("regular")
    regular = urls.get("regular") or urls.get("small") or original
    pid = item.get("pid") or item.get("id")
    detail_url = item.get("detail_url") or item.get("url")
    if pid and not detail_url:
        detail_url = f"https://www.pixiv.net/artworks/{pid}"
    return normalize_recommendation_item({
        "title": item.get("title"), "subtitle": user.get("name") or item.get("user_name") or item.get("author") or item.get("userName"),
        "image": item.get("image") or item.get("image_url") or original or item.get("url"),
        "thumbnail": item.get("thumbnail") or item.get("thumbnail_url") or regular,
        "detail_url": detail_url,
        "description": item.get("description"), "rank_label": "DAILY",
    }, source="Pixiv")


@register_provider("pixiv_daily")
async def generate_pixiv_daily(mode_def, content_cfg, fallback, **kwargs):
    config = kwargs.get("config") or {}; override = config.get("mode_overrides", {}).get("PIXIV_DAILY", {})
    if not isinstance(override, dict): override = {}
    settings = config.get("mode_settings") or {}
    custom_endpoint = override.get("endpoint") or settings.get("endpoint") or content_cfg.get("endpoint")
    
    proxy_url = resolve_proxy_url(config.get("global_proxy_url"))
    endpoints = [custom_endpoint] if custom_endpoint else [_PRIMARY_ENDPOINT, _MIRROR_ENDPOINT]

    parsed_items = []
    for ep in endpoints:
        if not ep:
            continue
        try:
            headers = {"Accept": "application/json", "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)", "Referer": "https://www.pixiv.net/"}
            policy = RequestPolicy(
                timeout=httpx.Timeout(connect=2.5, read=5.0, write=3.0, pool=2.5),
                max_attempts=1 if not proxy_url else 2,
                follow_redirects=True,
            )
            response = await asyncio.to_thread(
                outbound_http.get_json,
                ep,
                headers=headers,
                proxy_url=proxy_url,
                policy=policy,
            )
            items = _parse_pixiv_items(response.json())
            if items:
                parsed_items = items
                break
        except Exception:
            continue

    if not parsed_items:
        return {**_FALLBACK, "layout_style": override.get("layout_style", "cover_card")}

    first_item = parsed_items[0]
    return {
        "title": first_item.get("title") or "Pixiv 每日一图",
        "subtitle": first_item.get("subtitle") or "每日精选插画",
        "source": "Pixiv",
        "rank_label": first_item.get("rank_label") or "DAILY",
        "items": parsed_items,
        "layout_style": override.get("layout_style", "cover_card"),
    }
