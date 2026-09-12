"""Shared normalization helpers for external recommendation providers."""
from __future__ import annotations

from typing import Any
from urllib.parse import urlparse


def resolve_proxy_url(value: Any, *, auto_detect: bool = False) -> str | None:
    if isinstance(value, str) and value.strip():
        val = value.strip()
        parsed = urlparse(val)
        if parsed.scheme.lower() in {"http", "https", "socks5", "socks5h"} and parsed.hostname:
            return val

    if not auto_detect:
        return None

    # 自动环境探测与本地代理回退（支持 Docker 容器互联 mihomo 与宿主机标准代理）
    import os
    import socket

    env_proxy = os.getenv("INKSIGHT_GLOBAL_PROXY_URL") or os.getenv("HTTP_PROXY") or os.getenv("http_proxy")
    if env_proxy and isinstance(env_proxy, str):
        parsed = urlparse(env_proxy.strip())
        if parsed.scheme.lower() in {"http", "https", "socks5", "socks5h"} and parsed.hostname:
            return env_proxy.strip()

    # 尝试探测常见的内置代理端点（mihomo-cliproxy 或 127.0.0.1:7891 / 7890）
    candidate_endpoints = [
        ("socks5://mihomo-cliproxy:7890", "mihomo-cliproxy", 7890),
        ("http://mihomo-cliproxy:7890", "mihomo-cliproxy", 7890),
        ("http://127.0.0.1:7891", "127.0.0.1", 7891),
        ("http://127.0.0.1:7890", "127.0.0.1", 7890),
    ]
    for proxy_str, host, port in candidate_endpoints:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.15)
                if s.connect_ex((host, port)) == 0:
                    return proxy_str
        except Exception:
            continue

    return None


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
    if "fallback_image" in payload and payload["fallback_image"] is not None:
        res["fallback_image"] = payload["fallback_image"]
    return res
