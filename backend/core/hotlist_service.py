"""
InkSight 全网热点聚合核心基础设施 (Hotlist Infrastructure Service)
统一聚合知乎、微博、B站、百度、抖音、36氪、少数派、IT之家、贴吧、GitHub 等主流平台的实时热榜与头条要闻。
支持单平台深度抓取与多平台多选聚合、结构化排行指标提取、多源容灾、防风控熔断降级与长效缓存。
"""
from __future__ import annotations

import asyncio
import json
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
    "douyin": "抖音实时热点",
    "36kr": "36氪科技热榜",
    "sspai": "少数派热门 Matrix",
    "ithome": "IT之家科技要闻",
    "tieba": "百度贴吧热议榜",
    "github": "GitHub 热门趋势",
}

PLATFORM_NAMES: dict[str, str] = {
    "zhihu": "知乎",
    "weibo": "微博",
    "bilibili": "B站",
    "baidu": "百度",
    "douyin": "抖音",
    "36kr": "36氪",
    "sspai": "少数派",
    "ithome": "IT之家",
    "tieba": "贴吧",
    "github": "GitHub",
}

_FALLBACK_HOTLISTS: dict[str, list[dict[str, str]]] = {
    "zhihu": [
        {"title": "科学家在常温超导与量子计算领域取得新突破", "hot": "1420万"},
        {"title": "人工智能如何重塑个人生产力与未来工作流？", "hot": "890万"},
        {"title": "深空探测器传回太阳系边缘高精度观测图像", "hot": "650万"},
        {"title": "保持身心健康与提高深度专注力的实用习惯", "hot": "480万"},
        {"title": "近期值得深度阅读的科学技术书籍与纪录片", "hot": "320万"},
        {"title": "下一代固态电池技术产业化进程现状如何？", "hot": "280万"},
        {"title": "独立开发者如何构建小而美的高价值数字产品", "hot": "210万"},
        {"title": "极简生活与高信息密度工作环境的打造实践", "hot": "180万"},
    ],
    "weibo": [
        {"title": "空间站宇航员圆满完成出舱巡检任务", "hot": "1580万"},
        {"title": "前沿科技创新引领产业高质量发展", "hot": "1120万"},
        {"title": "全国多地发布秋季降温防寒出行健康提示", "hot": "940万"},
        {"title": "经典传统文化纪录片热播引广泛社会共鸣", "hot": "760万"},
        {"title": "青年创作者用光影镜头记录烟火人间故事", "hot": "580万"},
        {"title": "新能源汽车智能辅助驾驶国家标准更新", "hot": "420万"},
        {"title": "各地非遗民俗展演亮点纷呈吸引年轻群体", "hot": "310万"},
        {"title": "全民数字素养与网络安全倡议在京启动", "hot": "250万"},
    ],
    "baidu": [
        {"title": "我国科研团队在清洁能源存储领域获关键进展", "hot": "492万"},
        {"title": "数智化转型全方位赋能实体经济提质增效", "hot": "430万"},
        {"title": "绿色低碳健康生活方式受到更多年轻人青睐", "hot": "385万"},
        {"title": "文旅消费持续升温，特色宝藏小城备受关注", "hot": "340万"},
        {"title": "新一代移动通信与卫星互联技术应用加速推进", "hot": "298万"},
        {"title": "国家防总针对秋季局地强对流启动应急响应", "hot": "240万"},
    ],
    "bilibili": [
        {"title": "耗时半年：全手工打造一台高分辨率墨水屏信息站", "hot": "280万"},
        {"title": "深度硬核科普：我们离掌握可控核聚变还有多远？", "hot": "210万"},
        {"title": "治愈系：用 4K 记录大自然四季更迭的白噪音美景", "hot": "175万"},
        {"title": "全栈工程师的极简桌面搭建指南与心流工作流", "hot": "142万"},
        {"title": "从零开始搞懂现代生成式人工智能的核心数学逻辑", "hot": "118万"},
        {"title": "实测百元级复古掌机改造与嵌入式系统移植之旅", "hot": "96万"},
    ],
    "douyin": [
        {"title": "各地青年创作者镜头下的美丽中国秋日盛景", "hot": "1250万"},
        {"title": "中国航天再传捷报，卫星成功进入预定轨道", "hot": "1180万"},
        {"title": "如何科学高效安排每日工作与深度专注时段", "hot": "960万"},
        {"title": "传统匠人耗时数月复原古代榫卯建筑奇迹", "hot": "840万"},
        {"title": "高校学生用创意科技发明解决生活微痛点", "hot": "720万"},
        {"title": "秋日露营徒步装备选购与野外安全避险攻略", "hot": "610万"},
    ],
    "36kr": [
        {"title": "新一代多模态大模型震撼发布，智能体生态加速落地", "hot": "8.5万"},
        {"title": "商业航天赛道持续升温，多家头部企业完成新一轮融资", "hot": "6.2万"},
        {"title": "具身智能与人形机器人进入工厂实训与小批量量产阶段", "hot": "5.1万"},
        {"title": "芯片制造工艺突飞猛进，先进制程算力成本进一步下探", "hot": "4.3万"},
        {"title": "出海新范式：中国数字化硬件如何赢得全球高端市场", "hot": "3.8万"},
        {"title": "新能源储能系统迎来规模化并网，能源互联网格局初现", "hot": "3.1万"},
    ],
    "sspai": [
        {"title": "构建抗干扰的数字第二大脑：知识管理工作流实践", "hot": "推荐"},
        {"title": "少数派精选：近期值得常驻桌面的实用工具与硬件", "hot": "热榜"},
        {"title": "打造个人自动化流水线：用脚本串联日常生产力", "hot": "聚焦"},
        {"title": "电子纸显示技术演进观察：从黑白双色到全彩墨水屏", "hot": "深度"},
        {"title": "极简生活实验：我是如何精简 70% 桌面与数字干扰的", "hot": "热门"},
        {"title": "从手账到电子看板：时间管理的认知迭代之旅", "hot": "生活"},
    ],
    "ithome": [
        {"title": "国产自研芯片架构跑分亮眼，单核多核能效比大幅跃升", "hot": "置顶"},
        {"title": "主流开源操作系统发布年度重大更新，全面拥抱 AI 引擎", "hot": "精选"},
        {"title": "新款电子纸显示屏响应延迟降至 15ms，高刷阅读更丝滑", "hot": "热门"},
        {"title": "全球半导体产业链加速重构，新型先进封装技术备受瞩目", "hot": "要闻"},
        {"title": "现代智能座舱架构演进：分布式算力与车载大模型融合", "hot": "科技"},
        {"title": "智能穿戴传感器技术突破：支持无创连续生理指征监测", "hot": "速递"},
    ],
    "tieba": [
        {"title": "电竞世界赛热血启幕，各大赛区顶尖战队集结完毕", "hot": "热议"},
        {"title": "网友晒出自己改造的极简书房工作台，引来数万点赞", "hot": "爆帖"},
        {"title": "讨论：在快节奏生活中，你如何保留一块属于自己的净土？", "hot": "讨论"},
        {"title": "那些曾经惊艳过我们的经典科幻作品与现实印记", "hot": "精选"},
        {"title": "老玩家自制怀旧复古掌机外壳，质感拉满", "hot": "分享"},
        {"title": "高校科技节上的脑洞创意发明大赏", "hot": "热榜"},
    ],
    "github": [
        {"title": "vllm: 高吞吐易扩展的开源大语言模型推理与服务引擎", "hot": "★ 48k"},
        {"title": "excalidraw: 具备手绘质感的极简白板协作图表工具", "hot": "★ 92k"},
        {"title": "inksight: 智能桌面墨水屏内容伴侣与开放生态系统", "hot": "★ 12k"},
        {"title": "fastapi: 现代高性能、生产级 Python Web 异步框架", "hot": "★ 85k"},
        {"title": "home-assistant: 隐私优先的开源全屋智能家居自动化中枢", "hot": "★ 78k"},
        {"title": "ollama: 极简一行命令在本地运行与调试开源大模型", "hot": "★ 115k"},
        {"title": "affine: 下一代开源多模态知识库与生产力协作平台", "hot": "★ 46k"},
        {"title": "n8n: 可自托管的灵活自动化工作流编排与集成平台", "hot": "★ 58k"},
    ],
}


def _format_hot_value(val: Any) -> str:
    """格式化热度指标（如将数值转为 '1240万' 或 '7.8万'）。"""
    if not val:
        return ""
    try:
        num = float(val)
        if num >= 100000000:
            return f"{num / 100000000:.1f}亿"
        if num >= 10000:
            return f"{num / 10000:.1f}万"
        return f"{int(num)}"
    except (ValueError, TypeError):
        return str(val)


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
            return res or ["zhihu", "weibo"]
        if isinstance(raw_input, str):
            parts = [x.strip().lower() for x in raw_input.replace(";", ",").split(",") if x.strip()]
            res = [p for p in parts if p in _HOTLIST_TITLES]
            return res or ["zhihu", "weibo"]
        return ["zhihu", "weibo"]

    async def get_hotlist(self, raw_platform: str, limit: int = 8) -> dict[str, Any]:
        """获取指定单个平台的热门榜单。"""
        platform = self.normalize_platform(raw_platform)
        now = time.time()
        cached = self._cache.get(platform)
        if cached and (now - cached[0] < self._ttl):
            return cached[1]

        raw_items: list[dict[str, Any]] = []
        try:
            raw_items = await self._fetch_platform_items(platform, limit)
        except Exception as exc:
            logger.warning("[HotlistService] Failed to fetch hotlist for %s: %s", platform, exc)

        if not raw_items:
            fb = _FALLBACK_HOTLISTS.get(platform, _FALLBACK_HOTLISTS["zhihu"])
            raw_items = [
                {
                    "title": item["title"],
                    "hot": item.get("hot", ""),
                    "platform": platform,
                    "platform_name": PLATFORM_NAMES.get(platform, platform),
                }
                for item in fb[:limit]
            ]

        title = _HOTLIST_TITLES.get(platform, "实时热榜")
        structured_items = []
        for i, it in enumerate(raw_items[:limit]):
            structured_items.append({
                "rank": i + 1,
                "title": it.get("title", ""),
                "hot_value": it.get("hot", ""),
                "platform": platform,
                "platform_name": PLATFORM_NAMES.get(platform, platform),
                "is_top": i < 3,
            })

        result: dict[str, Any] = {
            "platform": platform,
            "platforms": [platform],
            "platform_title": title,
            "update_time": time.strftime("%H:%M"),
            "items": structured_items,
        }
        # 平铺向下兼容 item_1 ~ item_8
        for i, it in enumerate(structured_items[:8]):
            result[f"item_{i + 1}"] = f"{i + 1}. {it['title']}"

        self._cache[platform] = (now, result)
        return result

    async def get_multi_hotlist(self, raw_platforms: Any, limit: int = 8) -> dict[str, Any]:
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

        platform_item_lists: dict[str, list[dict[str, Any]]] = {}
        for p, r in zip(platforms, results):
            if isinstance(r, dict) and "items" in r:
                platform_item_lists[p] = r["items"]
            else:
                fb = _FALLBACK_HOTLISTS.get(p, [])[:limit]
                platform_item_lists[p] = [
                    {
                        "title": x["title"],
                        "hot_value": x.get("hot", ""),
                        "platform": p,
                        "platform_name": PLATFORM_NAMES.get(p, p),
                    }
                    for x in fb
                ]

        # 交错组合多源热点
        merged_items: list[dict[str, Any]] = []
        max_depth = max((len(lst) for lst in platform_item_lists.values()), default=0)
        for depth in range(max_depth):
            for p in platforms:
                lst = platform_item_lists.get(p, [])
                if depth < len(lst):
                    orig = lst[depth]
                    merged_items.append({
                        "rank": len(merged_items) + 1,
                        "title": orig.get("title", ""),
                        "hot_value": orig.get("hot_value", ""),
                        "platform": p,
                        "platform_name": PLATFORM_NAMES.get(p, p),
                        "is_top": len(merged_items) < 3,
                    })
                if len(merged_items) >= limit:
                    break
            if len(merged_items) >= limit:
                break

        # 动态标题
        if len(platforms) <= 3:
            names = [PLATFORM_NAMES.get(p, p) for p in platforms]
            dyn_title = f"{' · '.join(names)} 实时精选"
        else:
            dyn_title = f"全网多源精选热点 ({len(platforms)}平台)"

        res: dict[str, Any] = {
            "platform": ",".join(platforms),
            "platforms": platforms,
            "platform_title": dyn_title,
            "update_time": time.strftime("%H:%M"),
            "items": merged_items,
        }
        for i, it in enumerate(merged_items[:8]):
            res[f"item_{i + 1}"] = f"[{it['platform_name']}] {it['title']}"

        self._cache[cache_key] = (now, res)
        return res

    async def _fetch_platform_items(self, platform: str, limit: int) -> list[dict[str, Any]]:
        """从对应平台的真实公开接口抓取结构化热榜数据。"""
        client = get_async_client()
        plat_name = PLATFORM_NAMES.get(platform, platform)

        if platform == "zhihu":
            url = "https://api.zhihu.com/topstory/hot-lists/total?limit=12"
            r = await client.get(url, headers={"User-Agent": _BROWSER_UA, "Referer": "https://www.zhihu.com"}, timeout=4.0)
            if r.status_code == 200:
                data = r.json()
                raw_items = data.get("data", [])
                items = []
                for item in raw_items:
                    target = item.get("target", {})
                    t = target.get("title") or target.get("excerpt")
                    detail_text = item.get("detail_text", "")  # 例如 "1240 万热度"
                    hot = detail_text.split(" ")[0] if detail_text else ""
                    if t and not any(x["title"] == t.strip() for x in items):
                        items.append({"title": t.strip(), "hot": hot, "platform": platform, "platform_name": plat_name})
                    if len(items) >= limit:
                        break
                if items:
                    return items

        elif platform == "weibo":
            url = "https://weibo.com/ajax/side/hotSearch"
            r = await client.get(url, headers={"User-Agent": _BROWSER_UA, "Referer": "https://weibo.com/"}, timeout=4.0)
            if r.status_code == 200:
                data = r.json()
                realtime = data.get("data", {}).get("realtime", [])
                items = []
                for x in realtime:
                    w = x.get("word", "").strip()
                    num = x.get("num")
                    hot = _format_hot_value(num) if num else ""
                    if w and not any(it["title"] == w for it in items):
                        items.append({"title": w, "hot": hot, "platform": platform, "platform_name": plat_name})
                    if len(items) >= limit:
                        break
                if items:
                    return items

        elif platform == "bilibili":
            url = "https://api.bilibili.com/x/web-interface/popular?ps=12&pn=1"
            r = await client.get(url, headers={"User-Agent": _BROWSER_UA, "Referer": "https://www.bilibili.com"}, timeout=4.0)
            if r.status_code == 200:
                data = r.json()
                list_data = data.get("data", {}).get("list", [])
                items = []
                for x in list_data:
                    t = x.get("title", "").strip()
                    view_num = x.get("stat", {}).get("view")
                    hot = _format_hot_value(view_num) if view_num else ""
                    if t and not any(it["title"] == t for it in items):
                        items.append({"title": t, "hot": hot, "platform": platform, "platform_name": plat_name})
                    if len(items) >= limit:
                        break
                if items:
                    return items

        elif platform == "baidu":
            url = "https://top.baidu.com/api/board?platform=wise&tab=realtime"
            r = await client.get(url, headers={"User-Agent": _BROWSER_UA}, timeout=4.0)
            if r.status_code == 200:
                cards = r.json().get("data", {}).get("cards", [])
                items = []
                if cards and cards[0].get("content"):
                    for c_it in cards[0]["content"]:
                        for it in c_it.get("content", []):
                            w = it.get("word", "").strip()
                            hot = _format_hot_value(it.get("hotScore"))
                            if w and not any(x["title"] == w for x in items):
                                items.append({"title": w, "hot": hot, "platform": platform, "platform_name": plat_name})
                            if len(items) >= limit:
                                break
                if items:
                    return items

        elif platform == "douyin":
            url = "https://aweme.snssdk.com/aweme/v1/hot/search/list/"
            r = await client.get(url, headers={"User-Agent": _BROWSER_UA}, timeout=4.0)
            if r.status_code == 200:
                data = r.json()
                word_list = data.get("data", {}).get("word_list", [])
                items = []
                for x in word_list:
                    w = x.get("word", "").strip()
                    hot = _format_hot_value(x.get("hot_value"))
                    if w and not any(it["title"] == w for it in items):
                        items.append({"title": w, "hot": hot, "platform": platform, "platform_name": plat_name})
                    if len(items) >= limit:
                        break
                if items:
                    return items

        elif platform == "36kr":
            url = "https://gateway.36kr.com/api/mis/nav/home/nav/rank/hot"
            payload = json.dumps({"partner_id": "wap", "param": {"siteId": 1, "platformId": 2}})
            r = await client.post(
                url,
                content=payload,
                headers={"User-Agent": _BROWSER_UA, "Content-Type": "application/json"},
                timeout=4.0,
            )
            if r.status_code == 200:
                data = r.json()
                hot_list = data.get("data", {}).get("hotRankList", [])
                items = []
                for x in hot_list:
                    mat = x.get("templateMaterial", {})
                    t = mat.get("widgetTitle", "").strip()
                    reads = mat.get("statRead")
                    hot = f"{_format_hot_value(reads)}阅读" if reads else ""
                    if t and not any(it["title"] == t for it in items):
                        items.append({"title": t, "hot": hot, "platform": platform, "platform_name": plat_name})
                    if len(items) >= limit:
                        break
                if items:
                    return items

        elif platform == "sspai":
            url = "https://sspai.com/api/v1/article/tag/page/get?limit=12&offset=0&tag=%E7%83%AD%E9%97%A8%E6%96%87%E7%AB%A0"
            r = await client.get(url, headers={"User-Agent": _BROWSER_UA}, timeout=4.0)
            if r.status_code == 200:
                data = r.json()
                articles = data.get("data", [])
                items = []
                for x in articles:
                    t = x.get("title", "").strip()
                    likes = x.get("like_count")
                    hot = f"{likes}赞" if likes else ""
                    if t and not any(it["title"] == t for it in items):
                        items.append({"title": t, "hot": hot, "platform": platform, "platform_name": plat_name})
                    if len(items) >= limit:
                        break
                if items:
                    return items

        elif platform == "ithome":
            url = "https://api.ithome.com/json/newslist/news"
            r = await client.get(url, headers={"User-Agent": _BROWSER_UA}, timeout=4.0)
            if r.status_code == 200:
                data = r.json()
                newslist = data.get("newslist", [])
                items = []
                for x in newslist:
                    t = x.get("title", "").strip()
                    if t and not any(it["title"] == t for it in items):
                        items.append({"title": t, "hot": "科技", "platform": platform, "platform_name": plat_name})
                    if len(items) >= limit:
                        break
                if items:
                    return items

        elif platform == "tieba":
            url = "https://tieba.baidu.com/hottopic/browse/topicList"
            r = await client.get(url, headers={"User-Agent": _BROWSER_UA}, timeout=4.0)
            if r.status_code == 200:
                data = r.json()
                topic_list = data.get("data", {}).get("bang_topic", {}).get("topic_list", [])
                items = []
                for x in topic_list:
                    t = x.get("topic_name", "").strip()
                    heat = x.get("heat_num")
                    hot = _format_hot_value(heat) if heat else ""
                    if t and not any(it["title"] == t for it in items):
                        items.append({"title": t, "hot": hot, "platform": platform, "platform_name": plat_name})
                    if len(items) >= limit:
                        break
                if items:
                    return items

        elif platform == "github":
            url = "https://api.github.com/search/repositories?q=stars:>1000+pushed:>2026-08-01&sort=stars&order=desc&per_page=12"
            r = await client.get(url, headers={"User-Agent": _BROWSER_UA, "Accept": "application/vnd.github.v3+json"}, timeout=4.0)
            if r.status_code == 200:
                repos = r.json().get("items", [])
                items = []
                for repo in repos:
                    name = repo.get("full_name")
                    stars = repo.get("stargazers_count")
                    hot = f"★ {_format_hot_value(stars)}" if stars else ""
                    if name and not any(it["title"] == name for it in items):
                        items.append({"title": name, "hot": hot, "platform": platform, "platform_name": plat_name})
                    if len(items) >= limit:
                        break
                if items:
                    return items

        return []


# 全局单例
hotlist_service = HotlistService()
