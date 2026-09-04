"""
全网热榜聚合 Provider (Hotlist)
聚合知乎热榜、微博热搜、B站热门、GitHub Trending、百度热搜等实时热点。
支持内存短时缓存（10分钟）与离线精选兜底池，抗平台风控与断网。
"""
from __future__ import annotations

import logging
import time
from typing import Any

import httpx

from .base import register_provider

logger = logging.getLogger(__name__)

# 内存缓存：platform -> (timestamp, data_dict)
_HOTLIST_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}
_HOTLIST_CACHE_TTL = 600  # 10 分钟缓存

_FALLBACK_HOTLISTS: dict[str, dict[str, Any]] = {
    "zhihu": {
        "platform_title": "知乎今日热榜",
        "update_time": time.strftime("%H:%M"),
        "item_1": "1. 科学家在常温超导与量子计算领域取得新进展",
        "item_2": "2. 人工智能如何重塑个人生产力与工作流？",
        "item_3": "3. 航天探测器传回太阳系边缘高精图像",
        "item_4": "4. 保持身心健康、提高深度专注力的实用习惯",
        "item_5": "5. 近期值得深度阅读的书籍与纪录片推荐",
    },
    "weibo": {
        "platform_title": "微博实时热搜",
        "update_time": time.strftime("%H:%M"),
        "item_1": "1. 空间站宇航员顺利完成出舱任务",
        "item_2": "2. 科技创新引领高质量发展",
        "item_3": "3. 气象台发布秋季降温与穿衣指南",
        "item_4": "4. 经典文化纪录片热播引共鸣",
        "item_5": "5. 青年创作者用镜头记录烟火人间",
    },
    "github": {
        "platform_title": "GitHub Trending 今日热门",
        "update_time": time.strftime("%H:%M"),
        "item_1": "1. vllm: High-throughput LLM serving engine",
        "item_2": "2. excalidraw: Virtual whiteboard for sketching",
        "item_3": "3. inksight: Smart E-Ink desktop companion",
        "item_4": "4. fastapi: Modern high-performance web framework",
        "item_5": "5. home-assistant: Open source home automation",
    },
    "bilibili": {
        "platform_title": "哔哩哔哩热播推荐",
        "update_time": time.strftime("%H:%M"),
        "item_1": "1. 耗时半年：全手工打造一台桌面电子墨水屏日历",
        "item_2": "2. 原创深度科普：我们离星际航行还有多远？",
        "item_3": "3. 治愈系：大自然四季更迭的白噪音与视觉盛宴",
        "item_4": "4. 程序员的极简桌面搭建指南与工作流分享",
        "item_5": "5. 一小时搞懂大模型的核心工作原理",
    },
}


@register_provider("hotlist")
async def generate_hotlist(
    mode_def: dict[str, Any],
    content_cfg: dict[str, Any],
    fallback: dict[str, Any],
    **kwargs: Any,
) -> dict[str, Any]:
    config = kwargs.get("config") or {}
    mode_settings = config.get("mode_settings") or {}
    mode_overrides = config.get("mode_overrides") or {}
    override = mode_overrides.get("HOTLIST") or {}

    platform = "zhihu"
    if isinstance(override, dict) and override.get("platform"):
        platform = str(override["platform"]).strip().lower()
    elif isinstance(mode_settings, dict) and mode_settings.get("platform"):
        platform = str(mode_settings["platform"]).strip().lower()
    elif content_cfg.get("platform"):
        platform = str(content_cfg["platform"]).strip().lower()

    now = time.time()
    cached = _HOTLIST_CACHE.get(platform)
    if cached and (now - cached[0] < _HOTLIST_CACHE_TTL):
        return cached[1]

    # 尝试拉取开源热榜 API (如通过免费公开聚合节点)
    api_url = f"https://api.pearktrue.cn/api/dailyhot/?title={platform}"
    try:
        async with httpx.AsyncClient(timeout=4.0, verify=False) as client:
            resp = await client.get(api_url)
            if resp.status_code == 200:
                data = resp.json()
                raw_list = data.get("data", [])
                if isinstance(raw_list, list) and len(raw_list) >= 3:
                    items_dict: dict[str, str] = {}
                    for i in range(min(5, len(raw_list))):
                        title_str = str(raw_list[i].get("title", "")).strip()
                        items_dict[f"item_{i+1}"] = f"{i+1}. {title_str[:28]}"

                    platform_names = {
                        "zhihu": "知乎实时热榜",
                        "weibo": "微博实时热搜",
                        "bilibili": "哔哩哔哩热门",
                        "github": "GitHub 热门项目",
                    }
                    result = {
                        "platform_title": platform_names.get(platform, f"{platform.upper()} 今日热榜"),
                        "update_time": time.strftime("%H:%M"),
                        **items_dict,
                    }
                    # 补齐不足 5 条的情况
                    for j in range(1, 6):
                        if f"item_{j}" not in result:
                            result[f"item_{j}"] = ""
                    _HOTLIST_CACHE[platform] = (now, result)
                    return result
    except Exception as exc:
        logger.info(f"[HotlistProvider] Public fetch failed for {platform}, using local curated pool: {exc}")

    fb = dict(fallback if fallback else _FALLBACK_HOTLISTS.get(platform, _FALLBACK_HOTLISTS["zhihu"]))
    fb["update_time"] = time.strftime("%H:%M")
    return fb
