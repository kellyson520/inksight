"""Public Pornhub recommendation adapter; no login or access-control bypass."""
from __future__ import annotations
import asyncio
from typing import Any
from ..outbound_http import RequestPolicy, outbound_http
from ..recommendation_provider import normalize_recommendation_item, resolve_proxy_url
from .base import register_provider

_FALLBACK = [{"title": "P站公开视频推荐", "subtitle": "公开榜单暂不可用", "source": "P站", "rank_label": "推荐"}]


def _parse_porn_items(payload: Any) -> list[dict[str, Any]]:
    raw = payload.get("videos", payload.get("data", payload)) if isinstance(payload, dict) else payload
    if not isinstance(raw, list): return []
    result=[]
    for index,item in enumerate(raw[:10],1):
        if not isinstance(item,dict): continue
        result.append(normalize_recommendation_item({"title":item.get("title"),"subtitle":item.get("username") or item.get("uploader"),"thumbnail":item.get("thumbnail") or item.get("thumb"),"detail_url":item.get("url"),"rank_label":f"NO.{index}"},source="P站"))
    return result


@register_provider("porn_video")
async def generate_porn_video(mode_def, content_cfg, fallback, **kwargs):
    config=kwargs.get("config") or {}; override=config.get("mode_overrides", {}).get("PORN_VIDEO", {})
    endpoint=override.get("endpoint") or content_cfg.get("endpoint"); items=[]
    if endpoint:
        try:
            response=await asyncio.to_thread(outbound_http.get_json, endpoint, proxy_url=resolve_proxy_url(config.get("global_proxy_url")), policy=RequestPolicy(max_attempts=1, follow_redirects=True)); items=_parse_porn_items(response.json())
        except Exception: pass
    return {"title":"P站视频推荐","source":"P站","items":items or _FALLBACK,"layout_style":override.get("layout_style","ranking")}
