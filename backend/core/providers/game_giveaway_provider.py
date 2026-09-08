"""Public game giveaway data provider for the 喜加一 display mode."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any
from urllib.parse import urlparse

from ..outbound_http import RequestPolicy, outbound_http
from .base import register_provider

logger = logging.getLogger(__name__)

_DEFAULT_FALLBACK: dict[str, Any] = {
    "source": "EPIC",
    "source_label": "EPIC",
    "game_title": "The Escapists 2",
    "deadline_label": "限时领取",
    "cover_url": "",
    "claim_url": "https://store.epicgames.com/",
    "description": "本周免费领取游戏",
}


def _safe_https_url(value: Any) -> str:
    value = str(value or "").strip()
    parsed = urlparse(value)
    if parsed.scheme == "https" and parsed.netloc:
        return value
    return ""


def _source_label(value: Any) -> str:
    value = str(value or "").strip().upper()
    if "STEAM" in value:
        return "STEAM"
    return "EPIC"


def _deadline_label(value: Any) -> str:
    if not value:
        return "限时领取"
    text = str(value).strip()
    try:
        normalized = text.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
        return f"截止 {parsed.strftime('%Y-%m-%d %H:%M')}"
    except (TypeError, ValueError):
        return "限时领取"


def _normalize_payload(payload: dict[str, Any], fallback: dict[str, Any]) -> dict[str, Any]:
    source = _source_label(payload.get("source", payload.get("platform", fallback.get("source"))))
    title = str(payload.get("game_title", payload.get("title", payload.get("name", fallback.get("game_title", "喜加一游戏")))) or "喜加一游戏").strip()
    cover_url = _safe_https_url(payload.get("cover_url", payload.get("image", payload.get("header_image", fallback.get("cover_url")))))
    if not cover_url:
        # 保证断网/接口失败时仍有可视封面背景；该 SVG 不含外部资源或私密信息。
        cover_url = "https://dummyimage.com/640x360/e8e8e8/222222.png&text=GAME+GIVEAWAY"
    claim_url = _safe_https_url(payload.get("claim_url", payload.get("url", fallback.get("claim_url"))))
    return {
        "source": source,
        "source_label": source,
        "game_title": title[:120],
        "deadline_label": _deadline_label(payload.get("deadline", payload.get("expires_at", payload.get("end_time")))),
        "cover_url": cover_url,
        "claim_url": claim_url,
        "description": str(payload.get("description", fallback.get("description", "限时免费领取")) or "限时免费领取").strip()[:180],
    }


async def _fetch_giveaway_payload(endpoint: str) -> dict[str, Any]:
    response = await outbound_http.get_json(
        endpoint,
        policy=RequestPolicy(max_attempts=1, follow_redirects=False),
    )
    data = response.json()
    return data if isinstance(data, dict) else {}


@register_provider("game_giveaway")
async def generate_game_giveaway(
    mode_def: dict[str, Any],
    content_cfg: dict[str, Any],
    fallback: dict[str, Any],
    **kwargs: Any,
) -> dict[str, Any]:
    config = kwargs.get("config") or {}
    overrides = config.get("mode_overrides", {}).get("GAME_GIVEAWAY", {})
    if not isinstance(overrides, dict):
        overrides = {}

    base = dict(_DEFAULT_FALLBACK)
    base.update(fallback or {})
    endpoint = overrides.get("endpoint") or content_cfg.get("endpoint")
    payload: dict[str, Any] = {}
    if isinstance(endpoint, str) and _safe_https_url(endpoint):
        try:
            payload = await _fetch_giveaway_payload(endpoint)
        except Exception as exc:
            logger.warning("[GameGiveaway] public endpoint unavailable: %s", type(exc).__name__)

    merged = dict(payload)
    merged.update({key: value for key, value in overrides.items() if key != "endpoint" and value not in (None, "")})
    return _normalize_payload(merged, base)
