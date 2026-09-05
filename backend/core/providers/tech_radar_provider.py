"""
科技雷达与开源动态数据源 Provider (Tech Radar Provider)
将极客科技雷达数据解耦集成进 InkSight 模块化 Provider 体系。
【规范约束】：严格禁止 Emoji。
"""
from __future__ import annotations

import logging
from typing import Any

from core.providers.base import register_provider
from core.tech_radar_service import tech_radar_service

logger = logging.getLogger(__name__)


@register_provider("tech_radar")
async def generate_tech_radar(
    mode_def: dict[str, Any],
    content_cfg: dict[str, Any],
    fallback: dict[str, Any],
    **kwargs: Any,
) -> dict[str, Any]:
    """生成极客科技雷达内容。"""
    config = kwargs.get("config") or {}
    category = str(config.get("tech_category") or "ALL")
    try:
        data = await tech_radar_service.get_tech_radar_data(category=category)
        return data
    except Exception as e:
        logger.warning("[TechRadarProvider] Error generating tech radar: %s", e)
        return dict(fallback)
