"""
InkSight 全网热点聚合核心基础设施 (Hotlist Infrastructure Service)
统一聚合知乎、微博、B站、百度、GitHub 等主流平台的实时热榜与头条要闻。
支持单平台深度抓取与多平台多选聚合、多源容灾、防风控熔断降级与长效缓存。
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from .http_client import get_async_client

logger = logging.getLogger(__name__)

_BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)

_HOTLIST_TITLES: dict[str, str] = {
    "zhihu": "知乎实时热榜",
    "weibo": "微博实时热搜",
    "bilibili": "哔哩哔哩热门推荐",
    "baidu": "百度今日热搜",
    "github": "GitHub 热门趋势",
}

PLATFORM_NAMES: dict[str, str] = {
    "zhihu": "知乎",
    "weibo": "微博",
    "bilibili": "B站",
    "baidu": "百度",
    "github": "GitHub",
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
    "baidu": [
        "我国科研团队在清洁能源领域取得关键突破",
        "数字化转型赋能实体经济高质量发展",
        "健康生活理念受到更多年轻人关注",
        "文旅消费持续升温，特色小城受青睐",
        "新一代通信技术研发应用加速推进",
    ],
    "bilibili": [
        "耗时半年：全手工打造一台桌面电子墨水屏日历",
        "原创深度科普：我们离星际航行还有多远？",
        "治愈系：大自然四季更迭的白噪音与视觉盛宴",
        "程序员的极简桌面搭建指南与工作流分享",
        "一小时搞懂大模型的核心工作原理",
    ],
    "github": [
        "vllm: High-throughput LLM serving engine",
        "excalidraw: Virtual whiteboard for sketching",
        "inksight: Smart E-Ink desktop companion",
        "fastapi: Modern high-performance web framework",
        "home-assistant: Open source home automation",
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

    def parse_platforms(self, raw_input: Any) -> list[str]:
        """解析用户配置的多选平台（支持 list 或逗号/空格分隔字符串）。"""
        if isinstance(raw_input, list):
            res = []
            for p in raw_input:
                s = str(p).strip().lower()
                if s in _HOTLIST_TITLES and s not in res:
                    res.append(s)
            return res or ["zhihu"]
        if isinstance(raw_input, str):
            parts = [x.strip().lower() for x in raw_input.replace(";", ",").split(",") if x.strip()]
            res = [p for p in parts if p in _HOTLIST_TITLES]
            return res or ["zhihu"]
        return ["zhihu"]

    async def get_hotlist(self, raw_platform: str, limit: int = 5) -> dict[str, Any]:
        """获取指定单个平台的热门榜单。"""
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

    async def get_multi_hotlist(self, raw_platforms: Any, limit: int = 5) -> dict[str, Any]:
        """获取多平台多选聚合热榜，交错混合各平台头条，形成多源热点精选。"""
        platforms = self.parse_platforms(raw_platforms)
        if len(platforms) == 1:
            return await self.get_hotlist(platforms[0], limit)

        cache_key = "multi:" + ",".join(sorted(platforms))
        now = time.time()
        cached = self._cache.get(cache_key)
        if cached and (now - cached[0] < self._ttl):
            return cached[1]

        # 并发获取各个平台热点
        tasks = [self.get_hotlist(p, limit=limit) for p in platforms]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        platform_item_lists: dict[str, list[str]] = {}
        for p, r in zip(platforms, results):
            if isinstance(r, dict) and "items" in r:
                platform_item_lists[p] = [it.get("title", "") for it in r["items"] if it.get("title")]
            else:
                platform_item_lists[p] = _FALLBACK_HOTLISTS.get(p, [])[:limit]

        # 交错组合多源热点
        merged_items: list[str] = []
        max_depth = max((len(lst) for lst in platform_item_lists.values()), default=0)
        for depth in range(max_depth):
            for p in platforms:
                lst = platform_item_lists.get(p, [])
                if depth < len(lst):
                    t = lst[depth]
                    tag = PLATFORM_NAMES.get(p, p)
                    clean_t = t.strip()
                    merged_items.append(f"[{tag}] {clean_t}")
                if len(merged_items) >= limit:
                    break
            if len(merged_items) >= limit:
                break

        # 动态标题
        if len(platforms) == 2:
            names = [PLATFORM_NAMES.get(p, p) for p in platforms]
            dyn_title = f"{' · '.join(names)} 实时热搜"
        else:
            dyn_title = "全网多源精选热点"

        res: dict[str, Any] = {
            "platform": ",".join(platforms),
            "platforms": platforms,
            "platform_title": dyn_title,
            "update_time": time.strftime("%H:%M"),
            "items": [{"rank": i + 1, "title": it} for i, it in enumerate(merged_items)],
        }
        for i, it in enumerate(merged_items[:5]):
            res[f"item_{i + 1}"] = f"{i + 1}. {it}"

        self._cache[cache_key] = (now, res)
        return res

    async def _fetch_platform_items(self, platform: str, limit: int) -> list[str]:
        client = get_async_client()

        if platform == "zhihu":
            url = "https://api.zhihu.com/topstory/hot-lists/total?limit=10"
            r = await client.get(url, headers={"User-Agent": _BROWSER_UA, "Referer": "https://www.zhihu.com"}, timeout=4.0)
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
            url = "https://api.bilibili.com/x/web-interface/popular?ps=10&pn=1"
            r = await client.get(url, headers={"User-Agent": _BROWSER_UA, "Referer": "https://www.bilibili.com"}, timeout=4.0)
            if r.status_code == 200:
                data = r.json()
                list_data = data.get("data", {}).get("list", [])
                titles = [x.get("title", "").strip() for x in list_data if x.get("title")]
                if titles:
                    return titles[:limit]

        elif platform == "weibo":
            url = "https://weibo.com/ajax/side/hotSearch"
            r = await client.get(url, headers={"User-Agent": _BROWSER_UA, "Referer": "https://weibo.com/"}, timeout=4.0)
            if r.status_code == 200:
                data = r.json()
                realtime = data.get("data", {}).get("realtime", [])
                titles = [x.get("word", "").strip() for x in realtime if x.get("word")]
                if titles:
                    return titles[:limit]

        elif platform == "baidu":
            url = "https://top.baidu.com/api/board?platform=wise&tab=realtime"
            r = await client.get(url, headers={"User-Agent": _BROWSER_UA}, timeout=4.0)
            if r.status_code == 200:
                cards = r.json().get("data", {}).get("cards", [])
                bd_items = []
                if cards and cards[0].get("content"):
                    for c_it in cards[0]["content"]:
                        for it in c_it.get("content", []):
                            w = it.get("word")
                            if w and w not in bd_items:
                                bd_items.append(w.strip())
                if bd_items:
                    return bd_items[:limit]

        elif platform == "github":
            # GitHub Search API for trending active repositories
            url = "https://api.github.com/search/repositories?q=stars:>1000+pushed:>2026-08-01&sort=stars&order=desc&per_page=10"
            r = await client.get(url, headers={"User-Agent": _BROWSER_UA, "Accept": "application/vnd.github.v3+json"}, timeout=4.0)
            if r.status_code == 200:
                repos = r.json().get("items", [])
                titles = []
                for repo in repos:
                    name = repo.get("full_name")
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
