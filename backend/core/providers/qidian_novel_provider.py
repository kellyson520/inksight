"""Qidian novel recommendation provider."""
from __future__ import annotations
import asyncio
import json
import re
from typing import Any
from PIL import Image, ImageDraw
from ..outbound_http import RequestPolicy, outbound_http
from ..recommendation_provider import normalize_recommendation_item, resolve_proxy_url
from .base import register_provider

_DEFAULT_ENDPOINT = "https://m.qidian.com/rank"
_FALLBACK_COVER = "https://bookcover.yuewen.com/qdbimg/349573/1010868264/300"


def _local_fallback_image() -> Image.Image:
    image = Image.new("RGB", (400, 560), (242, 238, 230))
    draw = ImageDraw.Draw(image)
    draw.rectangle([20, 20, 380, 540], outline=(60, 50, 40), width=4)
    draw.line((40, 20, 40, 540), fill=(180, 170, 160), width=3)
    draw.text((120, 220), "起点中文网", fill=(40, 30, 20))
    draw.text((110, 280), "热门小说精选", fill=(80, 70, 60))
    return image


_FALLBACK = [
    {
        "title": "诡秘之主",
        "subtitle": "爱潜水的乌贼 · 异世大陆",
        "rank_label": "NO.1",
        "source": "起点小说",
        "cover_url": _FALLBACK_COVER,
        "thumbnail_url": _FALLBACK_COVER,
        "detail_url": "https://m.qidian.com/book/1010868264/",
        "description": "蒸汽与机械的浪潮中，谁能触及非凡？",
        "image_data": _local_fallback_image(),
    },
    {
        "title": "宿命之环",
        "subtitle": "爱潜水的乌贼 · 西方奇幻",
        "rank_label": "NO.2",
        "source": "起点小说",
        "cover_url": "https://bookcover.yuewen.com/qdbimg/349573/1036370336/300",
        "thumbnail_url": "https://bookcover.yuewen.com/qdbimg/349573/1036370336/300",
        "detail_url": "https://m.qidian.com/book/1036370336/",
        "description": "诡秘世界第二部。",
    },
    {
        "title": "道诡异仙",
        "subtitle": "狐尾的笔 · 东方玄幻",
        "rank_label": "NO.3",
        "source": "起点小说",
        "cover_url": "https://bookcover.yuewen.com/qdbimg/349573/1031794711/300",
        "thumbnail_url": "https://bookcover.yuewen.com/qdbimg/349573/1031794711/300",
        "detail_url": "https://m.qidian.com/book/1031794711/",
        "description": "诡异修仙世界。",
    },
]


def _parse_qidian_items(payload: Any) -> list[dict[str, Any]]:
    # 1. If payload is a raw HTML string from m.qidian.com/rank
    if isinstance(payload, str):
        match = re.search(r"<script[^>]*>\s*(\{.*?\"pageContext\".*?\})\s*</script>", payload, re.DOTALL)
        if match:
            try:
                raw_json = re.sub(r":\s*!undefined", ": null", match.group(1))
                data = json.loads(raw_json)
                pd = data.get("pageContext", {}).get("pageProps", {}).get("pageData", {})
                rank_list = pd.get("hotRank") or pd.get("readIndex") or pd.get("recRank") or []
                if rank_list:
                    result = []
                    for idx, b in enumerate(rank_list[:10], 1):
                        bid = str(b.get("bid") or "")
                        cover = f"https://bookcover.yuewen.com/qdbimg/349573/{bid}/300" if bid else ""
                        auth = str(b.get("bAuth") or "").strip()
                        cat = str(b.get("cat") or "").strip()
                        subtitle = auth + (f" · {cat}" if cat else "")
                        result.append(
                            normalize_recommendation_item(
                                {
                                    "title": b.get("bName"),
                                    "subtitle": subtitle,
                                    "cover_url": cover,
                                    "thumbnail_url": cover,
                                    "rank_label": f"NO.{idx}",
                                    "detail_url": f"https://m.qidian.com/book/{bid}/" if bid else "",
                                    "description": b.get("desc"),
                                },
                                source="起点小说",
                            )
                        )
                    if result:
                        return result
            except Exception:
                pass

        # Regex fallback for mobile html
        html_matches = re.findall(
            r"data-bid=[\"'](\d+)[\"'][^>]*>.*?<h2[^>]*>([^<]+)</h2>.*?<p[^>]*>([^<]+)</p>",
            payload,
            re.DOTALL,
        )
        if html_matches:
            result = []
            for idx, (bid, title, subtitle) in enumerate(html_matches[:10], 1):
                cover = f"https://bookcover.yuewen.com/qdbimg/349573/{bid}/300"
                result.append(
                    normalize_recommendation_item(
                        {
                            "title": title.strip(),
                            "subtitle": subtitle.strip(),
                            "cover_url": cover,
                            "thumbnail_url": cover,
                            "rank_label": f"NO.{idx}",
                            "detail_url": f"https://m.qidian.com/book/{bid}/",
                        },
                        source="起点小说",
                    )
                )
            if result:
                return result
        return []

    # 2. If payload is parsed JSON or dictionary
    raw = payload.get("data", payload.get("results", payload)) if isinstance(payload, dict) else payload
    if not isinstance(raw, list):
        return []
    result = []
    for index, item in enumerate(raw[:10], 1):
        if not isinstance(item, dict):
            continue
        bid = str(item.get("bid") or item.get("bookId") or item.get("id") or "").strip()
        cover = item.get("bookImg") or item.get("cover") or (f"https://bookcover.yuewen.com/qdbimg/349573/{bid}/300" if bid else "")
        result.append(
            normalize_recommendation_item(
                {
                    "title": item.get("bookName") or item.get("title") or item.get("name"),
                    "subtitle": item.get("authorName") or item.get("author"),
                    "cover_url": cover,
                    "thumbnail_url": cover,
                    "detail_url": item.get("bookUrl") or item.get("url") or (f"https://m.qidian.com/book/{bid}/" if bid else ""),
                    "rank_label": f"NO.{item.get('rank', index)}",
                    "description": item.get("description") or item.get("intro"),
                },
                source="起点小说",
            )
        )
    return result


@register_provider("qidian_novel")
async def generate_qidian_novel(mode_def, content_cfg, fallback, **kwargs):
    config = kwargs.get("config") or {}
    override = config.get("mode_overrides", {}).get("QIDIAN_NOVEL", {})
    if not isinstance(override, dict):
        override = {}
    settings = config.get("mode_settings") or {}
    endpoint = override.get("endpoint") or settings.get("endpoint") or content_cfg.get("endpoint") or _DEFAULT_ENDPOINT
    proxy_url = resolve_proxy_url(config.get("global_proxy_url"))
    items = []
    headers = {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Referer": "https://m.qidian.com/",
    }
    try:
        response = await asyncio.to_thread(
            outbound_http.get_text,
            endpoint,
            headers=headers,
            proxy_url=proxy_url,
            policy=RequestPolicy(max_attempts=2, follow_redirects=True),
        )
        items = _parse_qidian_items(response.text)
    except Exception:
        pass
    return {
        "title": "起点小说推荐",
        "source": "起点小说",
        "items": items or _FALLBACK,
        "layout_style": override.get("layout_style", "ranking"),
    }
