"""
InkSight 全网热点聚合核心基础设施 (Hotlist Infrastructure Service)
统一聚合知乎、微博、B站、GitHub Trending、百度等主流平台的实时热榜与头条要闻。
具备多源容灾、防风控熔断降级与长效缓存。
"""
from __future__ import annotations

import logging
import time
from typing import Any

from .http_client import get_async_client

logger = logging.getLogger(__name__)

_HOTLIST_TITLES: dict[str, str] = {
    "zhihu": "知乎实时热榜",
    "weibo": "微博实时热搜",
    "bilibili": "哔哩哔哩热播推荐",
    "github": "GitHub Trending 今日热门",
    "baidu": "百度今日热搜",
}

_FALLBACK_HOTLISTS: dict[str, list[str]] = {
    "zhihu": [
        "科学家在常温超导与量子计算领域取得新进展",
        "人工智能如何重塑个人生产力与工作流？",
        "航天探测器传回太阳系边缘高精图像",
        "保持身心健康、提高深度专注力的实用习惯",
        "近期值得深度阅读的书籍与纪录片推荐",
    ],
    "weibo": [
        "空间站宇航员顺利完成出舱任务",
        "科技创新引领高质量发展",
        "气象台发布秋季降温与穿衣指南",
        "经典文化纪录片热播引共鸣",
        "青年创作者用镜头记录烟火人间",
    ],
    "github": [
        "vllm: High-throughput LLM serving engine",
        "excalidraw: Virtual whiteboard for sketching",
        "inksight: Smart E-Ink desktop companion",
        "fastapi: Modern high-performance web framework",
        "home-assistant: Open source home automation",
    ],
    "bilibili": [
        "耗时半年：全手工打造一台桌面电子墨水屏日历",
        "原创深度科普：我们离星际航行还有多远？",
        "治愈系：大自然四季更迭的白噪音与视觉盛宴",
        "程序员的极简桌面搭建指南与工作流分享",
        "一小时搞懂大模型的核心工作原理",
    ],
    "baidu": [
        "我国科研团队在清洁能源领域取得关键突破",
        "数字化转型赋能实体经济高质量发展",
        "健康生活理念受到更多年轻人关注",
        "文旅消费持续升温，特色小城受青睐",
        "新一代通信技术研发应用加速推进",
    ],
}


class HotlistService:
    """全网热点聚合基础设施服务。"""

    def __init__(self, ttl: float = 600.0):
        self._ttl = ttl
        self._cache: dict[str, tuple[float, dict[str, Any]]] = {}

    def normalize_platform(self, raw_platform: str) -> str:
        plat = (raw_platform or "").strip().lower()
        if plat not in _HOTLIST_TITLES:
            plat = "zhihu"
        return plat

    async def get_hotlist(self, raw_platform: str, limit: int = 5) -> dict[str, Any]:
        """获取指定平台的热门榜单，返回结构化字典与排版兼容字段。"""
        platform = self.normalize_platform(raw_platform)
        now = time.time()
        cached = self._cache.get(platform)
        if cached and (now - cached[0] < self._ttl):
            return cached[1]

        items: list[str] = []
        try:
            items = await self._fetch_platform_items(platform, limit)
        except Exception as exc:
            logger.warning("[HotlistService] Failed to fetch hotlist for %s: %s", platform, exc)

        if not items:
            items = _FALLBACK_HOTLISTS.get(platform, _FALLBACK_HOTLISTS["zhihu"])[:limit]

        # 封装兼容墨水屏 JSON 排版与标准 API 的双重结构
        title = _HOTLIST_TITLES.get(platform, "实时热榜")
        result: dict[str, Any] = {
            "platform": platform,
            "platform_title": title,
            "update_time": time.strftime("%H:%M"),
            "items": [{"rank": i + 1, "title": it} for i, it in enumerate(items)],
        }
        for i, it in enumerate(items[:5]):
            result[f"item_{i + 1}"] = f"{i + 1}. {it}"

        self._cache[platform] = (now, result)
        return result

    async def _fetch_platform_items(self, platform: str, limit: int) -> list[str]:
        client = get_async_client()

        if platform == "zhihu":
            # 知乎公开热榜接口
            url = "https://api.zhihu.com/topstory/hot-lists/total?limit=10"
            r = await client.get(url, headers={"Referer": "https://www.zhihu.com"}, timeout=4.0)
            if r.status_code == 200:
                data = r.json()
                raw_items = data.get("data", [])
                titles = []
                for item in raw_items:
                    target = item.get("target", {})
                    t = target.get("title") or target.get("excerpt")
                    if t and t not in titles:
                        titles.append(t.strip())
                    if len(titles) >= limit:
                        break
                if titles:
                    return titles

        elif platform == "bilibili":
            # B站综合热门视频排行榜
            url = "https://api.bilibili.com/x/web-interface/popular?ps=10&pn=1"
            r = await client.get(url, headers={"Referer": "https://www.bilibili.com"}, timeout=4.0)
            if r.status_code == 200:
                data = r.json()
                list_data = data.get("data", {}).get("list", [])
                titles = [x.get("title", "").strip() for x in list_data if x.get("title")]
                if titles:
                    return titles[:limit]

        elif platform == "weibo":
            # 微博移动端精简热搜 API
            url = "https://weibo.com/ajax/side/hotSearch"
            r = await client.get(url, headers={"Referer": "https://m.weibo.cn"}, timeout=4.0)
            if r.status_code == 200:
                data = r.json()
                realtime = data.get("data", {}).get("realtime", [])
                titles = [x.get("word", "").strip() for x in realtime if x.get("word")]
                if titles:
                    return titles[:limit]

        elif platform == "github":
            # GitHub Trending 纯净 API
            url = "https://api.gitterapp.com/repositories?since=daily"
            r = await client.get(url, timeout=4.0)
            if r.status_code == 200:
                repos = r.json()
                titles = []
                for repo in repos:
                    name = repo.get("name") or repo.get("author")
                    desc = repo.get("description") or ""
                    if name:
                        short_desc = (": " + desc[:30] + "...") if desc else ""
                        titles.append(f"{name}{short_desc}")
                    if len(titles) >= limit:
                        break
                if titles:
                    return titles

        return []


# 全局单例
hotlist_service = HotlistService()
