"""Iwara public video recommendation provider."""
from __future__ import annotations
import asyncio
from typing import Any
from ..outbound_http import RequestPolicy, outbound_http
from ..recommendation_provider import normalize_recommendation_item, resolve_proxy_url
from .base import register_provider

_FALLBACK = [{"title": "Iwara 视频推荐", "subtitle": "公开推荐视频", "source": "iwara", "rank_label": "推荐"}]


def _parse_iwara_items(payload: Any) -> list[dict[str, Any]]:
    raw = payload.get("results", payload.get("data", payload)) if isinstance(payload, dict) else payload
    if not isinstance(raw, list): return []
    result=[]
    for index, item in enumerate(raw[:10], 1):
        if not isinstance(item, dict): continue
        user=item.get("user") if isinstance(item.get("user"), dict) else {}
        result.append(normalize_recommendation_item({"title": item.get("title"), "subtitle": user.get("username") or item.get("username"), "thumbnail": item.get("thumbnail") or item.get("thumbnailUrl"), "detail_url": item.get("url") or item.get("id"), "rank_label": f"NO.{index}"}, source="iwara"))
    return result


@register_provider("iwara_video")
async def generate_iwara_video(mode_def, content_cfg, fallback, **kwargs):
    config=kwargs.get("config") or {}; override=config.get("mode_overrides", {}).get("IWARA_VIDEO", {})
    endpoint=override.get("endpoint") or content_cfg.get("endpoint"); items=[]
    if endpoint:
        try:
            response=await asyncio.to_thread(outbound_http.get_json, endpoint, proxy_url=resolve_proxy_url(config.get("global_proxy_url")), policy=RequestPolicy(max_attempts=1, follow_redirects=True)); items=_parse_iwara_items(response.json())
        except Exception: pass
    return {"title":"iwara 视频推荐","source":"iwara","items":items or _FALLBACK,"layout_style":override.get("layout_style","cover_card")}
