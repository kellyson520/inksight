"""Qidian novel recommendation provider."""
from __future__ import annotations
import asyncio
from typing import Any
from ..outbound_http import RequestPolicy, outbound_http
from ..recommendation_provider import normalize_recommendation_item, resolve_proxy_url
from .base import register_provider

_DEFAULT_ENDPOINT = "https://www.qidian.com/rank/"
_FALLBACK = [{"title": "诡秘之主", "subtitle": "爱潜水的乌贼", "rank_label": "NO.1", "source": "起点小说"}]


def _parse_qidian_items(payload: Any) -> list[dict[str, Any]]:
    raw = payload.get("data", payload.get("results", payload)) if isinstance(payload, dict) else payload
    if not isinstance(raw, list): return []
    result = []
    for index, item in enumerate(raw[:10], 1):
        if not isinstance(item, dict): continue
        result.append(normalize_recommendation_item({
            "title": item.get("bookName") or item.get("title") or item.get("name"),
            "subtitle": item.get("authorName") or item.get("author"),
            "cover_url": item.get("bookImg") or item.get("cover"),
            "detail_url": item.get("bookUrl") or item.get("url"),
            "rank_label": f"NO.{item.get('rank', index)}",
            "description": item.get("description") or item.get("intro"),
        }, source="起点小说"))
    return result


@register_provider("qidian_novel")
async def generate_qidian_novel(mode_def, content_cfg, fallback, **kwargs):
    config = kwargs.get("config") or {}; override = config.get("mode_overrides", {}).get("QIDIAN_NOVEL", {})
    endpoint = override.get("endpoint") or content_cfg.get("endpoint") or _DEFAULT_ENDPOINT
    items = []
    try:
        response = await asyncio.to_thread(outbound_http.get_json, endpoint, proxy_url=resolve_proxy_url(config.get("global_proxy_url")), policy=RequestPolicy(max_attempts=1, follow_redirects=True))
        items = _parse_qidian_items(response.json())
    except Exception: pass
    return {"title": "起点小说推荐", "source": "起点小说", "items": items or _FALLBACK, "layout_style": override.get("layout_style", "ranking")}
