"""XKCD provider adapter for computed JSON modes."""
from __future__ import annotations

from typing import Any

from ..xkcd_service import get_daily_xkcd
from .base import register_provider


@register_provider("xkcd_comic")
async def generate_xkcd(
    mode_def: dict[str, Any],
    content_cfg: dict[str, Any],
    fallback: dict[str, Any],
    **kwargs: Any,
) -> dict[str, Any]:
    comic = await get_daily_xkcd()
    return {**fallback, **comic}
