"""
豆瓣高分电影推荐 Provider (Douban Movie Provider)
为墨水屏提供对标微信读书样式的电影推荐：
右侧竖版高清电影海报，左侧电影名、导演、豆瓣评分与高赞影评推荐理由。
【规范约束】：严格禁止 Emoji。
"""
from __future__ import annotations

import logging
from typing import Any

from core.douban_movie_service import douban_movie_service
from .base import register_provider

logger = logging.getLogger(__name__)


@register_provider("douban_movie")
async def generate_douban_movie(
    mode_def: dict[str, Any],
    content_cfg: dict[str, Any],
    fallback: dict[str, Any],
    **kwargs: Any,
) -> dict[str, Any]:
    config = kwargs.get("config") or {}
    mode_settings = config.get("mode_settings") or {}
    mode_overrides = config.get("mode_overrides") or {}
    override = mode_overrides.get("DOUBAN_MOVIE") or {}

    category = "ALL"
    movie_id = None
    if isinstance(override, dict):
        if override.get("category"):
            category = str(override["category"])
        if override.get("movie_id"):
            movie_id = str(override["movie_id"])
    elif isinstance(mode_settings, dict):
        if mode_settings.get("category"):
            category = str(mode_settings["category"])
        if mode_settings.get("movie_id"):
            movie_id = str(mode_settings["movie_id"])
    elif content_cfg.get("category"):
        category = str(content_cfg["category"])

    device_mac = kwargs.get("device_mac")
    date_ctx = kwargs.get("date_ctx") or {}
    date_str = date_ctx.get("date_str", "")
    seed = f"{device_mac}_{date_str}_{category}" if device_mac else None

    # 若选择了 HOT (实时热门)，尝试拉取线上 Rexxar 榜单
    if category == "HOT":
        try:
            online_items = await douban_movie_service.fetch_douban_online_items("movie_real_time_hotest")
            if online_items:
                import hashlib
                idx = int(hashlib.md5((seed or "default").encode("utf-8")).hexdigest(), 16) % len(online_items)
                sel = online_items[idx]
                return {
                    "id": sel["id"],
                    "title": sel["title"],
                    "title_bracketed": f"《{sel['title']}》",
                    "director": sel["director"],
                    "year": sel["year"],
                    "genre": sel["genre"],
                    "director_line": f"{sel['director']} · {sel['year']}",
                    "rating": sel["rating"],
                    "rating_label": f"豆瓣 {sel['rating']} 分",
                    "rating_people": sel["rating_people"],
                    "rank_tag": sel["rank_tag"],
                    "recommend_reason": sel["recommend_reason"],
                    "quote": sel["quote"],
                    "cover_url": sel["cover_url"],
                    "update_time": "热门",
                    "footer_label": "豆瓣电影 · 实时热门",
                    "footer_quote": sel["quote"],
                }
        except Exception as err:
            logger.debug("[DoubanMovieProvider] Failed to fetch online hot items: %s", err)

    try:
        data = douban_movie_service.get_recommended_movie(
            category=category,
            movie_id=movie_id,
            seed=seed,
        )
        if data:
            return data
    except Exception as exc:
        logger.warning("[DoubanMovieProvider] Failed to get movie recommendation: %s", exc)

    return dict(fallback)
