"""Shared normalization helpers for external recommendation providers."""
from __future__ import annotations

from typing import Any
from urllib.parse import urlparse


def resolve_proxy_url(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    value = value.strip()
    if not value:
        return None
    parsed = urlparse(value)
    if parsed.scheme.lower() not in {"http", "https", "socks5", "socks5h"} or not parsed.hostname:
        return None
    return value


def normalize_recommendation_item(payload: dict[str, Any] | None, *, source: str = "") -> dict[str, Any]:
    payload = payload if isinstance(payload, dict) else {}
    title = str(payload.get("title") or payload.get("name") or "未命名推荐").strip()
    cover_url = str(payload.get("cover_url") or payload.get("cover") or payload.get("image") or "").strip()
    thumbnail_url = str(payload.get("thumbnail_url") or payload.get("thumbnail") or cover_url).strip()
    res = {
        "title": title,
        "subtitle": str(payload.get("subtitle") or payload.get("author") or payload.get("uploader") or "").strip(),
        "source": str(payload.get("source") or source).strip(),
        "cover_url": cover_url,
        "thumbnail_url": thumbnail_url,
        "rank_label": str(payload.get("rank_label") or payload.get("rank") or "推荐").strip(),
        "published_at": str(payload.get("published_at") or payload.get("date") or "").strip(),
        "detail_url": str(payload.get("detail_url") or payload.get("url") or "").strip(),
        "description": str(payload.get("description") or payload.get("summary") or "").strip(),
        "duration": str(payload.get("duration") or "").strip(),
        "views_label": str(payload.get("views_label") or "").strip(),
        "rating_label": str(payload.get("rating_label") or "").strip(),
    }
    if "image_data" in payload and payload["image_data"] is not None:
        res["image_data"] = payload["image_data"]
    return res
