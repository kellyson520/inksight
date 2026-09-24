"""
游戏媒体与社区动态 Provider (Gaming Media & Community News Provider)
为墨水屏提供：
1. gcores_podcast: 机核 播客（选择机核播客栏目，收听最新一期节目）
2. gcores_news: 机核 资讯（阅读机核关于游戏、影视、科技与流行文化的最新资讯）
3. gcores_articles: 机核 文章（阅读机核作者与社区创作者关于游戏、文化、科技与生活方式的深度文章）
4. miyoushe_news: 米游社 公告（选择你关注的游戏，查看米游社最新公告、活动与资讯）
5. gamersky_news: 游民星空 单机资讯（浏览游民星空最新单机游戏资讯，了解新作与游戏动态）
6. chuapp_articles: 触乐 最新文章（阅读触乐最新文章，了解游戏与玩家背后的故事）
7. yystv_articles: 游研社 最新文章（阅读游研社最新的游戏故事、文化文章与玩家见闻）
"""
from __future__ import annotations

import html
import json
import logging
import re
import time
import xml.etree.ElementTree as ET
from typing import Any
import httpx

from core.recommendation_provider import resolve_proxy_url
from .base import register_provider

logger = logging.getLogger(__name__)

_CACHE_TTL = 1200  # 20 分钟缓存
_MEDIA_CACHE: dict[str, tuple[float, Any]] = {}


def _clean_text(s: str | None, max_len: int = 200) -> str:
    if not s:
        return ""
    # 去除 HTML 标签与实体
    clean = re.sub(r"<[^>]+>", "", s)
    clean = html.unescape(clean)
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean[:max_len]


# ==========================================
# 1. 机核 播客 (GCORES_PODCAST)
# ==========================================
@register_provider("gcores_podcast")
async def generate_gcores_podcast(
    mode_def: dict[str, Any],
    content_cfg: dict[str, Any],
    fallback: dict[str, Any],
    **kwargs: Any,
) -> dict[str, Any]:
    global _MEDIA_CACHE
    now = time.time()
    cache_key = "gcores_radios"

    config = kwargs.get("config") or {}
    proxy = resolve_proxy_url(config.get("global_proxy_url"), auto_detect=True)
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

    cached_data = None
    if cache_key in _MEDIA_CACHE:
        ts, items = _MEDIA_CACHE[cache_key]
        if now - ts < _CACHE_TTL and items:
            cached_data = items

    if not cached_data:
        url = "https://www.gcores.com/gapi/v1/radios?sort=-published-at&page[limit]=10"
        try:
            async with httpx.AsyncClient(proxy=proxy, timeout=8.0, headers=headers) as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    data = resp.json()
                    cached_data = data.get("data", [])
                    _MEDIA_CACHE[cache_key] = (now, cached_data)
        except Exception as exc:
            logger.warning("[GamingMedia] Failed to fetch Gcores radios: %s", exc)

    if cached_data and len(cached_data) > 0:
        radio = cached_data[0]
        attrs = radio.get("attributes", {})
        title = attrs.get("title", "")
        published_at = str(attrs.get("published-at", ""))[:10]

        # 从 JSON content block 中提取摘要文本
        raw_content = attrs.get("content", "")
        summary = ""
        if raw_content:
            try:
                content_obj = json.loads(raw_content)
                blocks = content_obj.get("blocks", [])
                texts = [b.get("text", "") for b in blocks if b.get("text")]
                # 排除纯时间轴制作人员声明
                meaningful = [t for t in texts if not t.startswith("本期时间轴制作") and len(t) > 10]
                summary = " ".join(meaningful[:2])
            except Exception:
                summary = _clean_text(raw_content, 120)

        cover = attrs.get("thumb", attrs.get("cover", ""))
        if not cover:
            cover = "https://dummyimage.com/640x360/e23e3e/ffffff.png&text=GCORES+RADIO"

        res = dict(fallback)
        res.update({
            "header_tag": "机核网 · 最新电台",
            "title": title or fallback.get("title", "机核电台节目"),
            "program_tag": "Gadio Pro · 深度对谈",
            "summary": summary[:110] or fallback.get("summary", "最新一期机核播客节目上线。"),
            "published_at": published_at or "近期上线",
            "cover_url": cover,
            "footer_label": "GCORES RADIO · 分享热爱的声音",
        })
        return res

    return dict(fallback)


# ==========================================
# 2. 机核 资讯 (GCORES_NEWS)
# ==========================================
@register_provider("gcores_news")
async def generate_gcores_news(
    mode_def: dict[str, Any],
    content_cfg: dict[str, Any],
    fallback: dict[str, Any],
    **kwargs: Any,
) -> dict[str, Any]:
    global _MEDIA_CACHE
    now = time.time()
    cache_key = "gcores_news"

    config = kwargs.get("config") or {}
    proxy = resolve_proxy_url(config.get("global_proxy_url"), auto_detect=True)
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

    cached_data = None
    if cache_key in _MEDIA_CACHE:
        ts, items = _MEDIA_CACHE[cache_key]
        if now - ts < _CACHE_TTL and items:
            cached_data = items

    if not cached_data:
        url = "https://www.gcores.com/gapi/v1/categories/2/articles?sort=-published-at&page[limit]=10"
        try:
            async with httpx.AsyncClient(proxy=proxy, timeout=8.0, headers=headers) as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    data = resp.json()
                    cached_data = data.get("data", [])
                    _MEDIA_CACHE[cache_key] = (now, cached_data)
        except Exception as exc:
            logger.warning("[GamingMedia] Failed to fetch Gcores news: %s", exc)

    if cached_data and len(cached_data) > 0:
        item = cached_data[0]
        attrs = item.get("attributes", {})
        title = attrs.get("title", "")
        desc = attrs.get("desc", "") or ""
        published_at = str(attrs.get("published-at", ""))[:16].replace("T", " ")
        cover = attrs.get("thumb", attrs.get("cover", ""))

        res = dict(fallback)
        res.update({
            "header_tag": "机核 · 每日游戏资讯",
            "title": title or fallback.get("title", "机核最新资讯"),
            "category_badge": "全球资讯",
            "summary": _clean_text(desc, 120) or fallback.get("summary", ""),
            "published_at": published_at or "今日更新",
            "cover_url": cover or fallback.get("cover_url", ""),
            "footer_label": "GCORES NEWS · 游戏影视科技速递",
        })
        return res

    return dict(fallback)


# ==========================================
# 3. 机核 文章 (GCORES_ARTICLES)
# ==========================================
@register_provider("gcores_articles")
async def generate_gcores_articles(
    mode_def: dict[str, Any],
    content_cfg: dict[str, Any],
    fallback: dict[str, Any],
    **kwargs: Any,
) -> dict[str, Any]:
    global _MEDIA_CACHE
    now = time.time()
    cache_key = "gcores_articles"

    config = kwargs.get("config") or {}
    proxy = resolve_proxy_url(config.get("global_proxy_url"), auto_detect=True)
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

    cached_data = None
    if cache_key in _MEDIA_CACHE:
        ts, items = _MEDIA_CACHE[cache_key]
        if now - ts < _CACHE_TTL and items:
            cached_data = items

    if not cached_data:
        url = "https://www.gcores.com/gapi/v1/articles?sort=-published-at&page[limit]=10"
        try:
            async with httpx.AsyncClient(proxy=proxy, timeout=8.0, headers=headers) as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    data = resp.json()
                    cached_data = data.get("data", [])
                    _MEDIA_CACHE[cache_key] = (now, cached_data)
        except Exception as exc:
            logger.warning("[GamingMedia] Failed to fetch Gcores articles: %s", exc)

    if cached_data and len(cached_data) > 0:
        item = cached_data[0]
        attrs = item.get("attributes", {})
        title = attrs.get("title", "")
        desc = attrs.get("desc", "") or ""
        published_at = str(attrs.get("published-at", ""))[:10]
        cover = attrs.get("thumb", attrs.get("cover", ""))

        res = dict(fallback)
        res.update({
            "header_tag": "机核 · 深度好文",
            "title": title or fallback.get("title", "机核深度专栏"),
            "author": "机核特约作者",
            "summary": _clean_text(desc, 130) or fallback.get("summary", ""),
            "published_at": published_at or "近期发布",
            "cover_url": cover or fallback.get("cover_url", ""),
            "footer_label": "GCORES ARTICLE · 游戏与文化深度探讨",
        })
        return res

    return dict(fallback)


# ==========================================
# 4. 米游社 公告 (MIYOUSHE_NEWS)
# ==========================================
@register_provider("miyoushe_news")
async def generate_miyoushe_news(
    mode_def: dict[str, Any],
    content_cfg: dict[str, Any],
    fallback: dict[str, Any],
    **kwargs: Any,
) -> dict[str, Any]:
    global _MEDIA_CACHE
    now = time.time()

    config = kwargs.get("config") or {}
    mode_settings = config.get("mode_settings", {}).get("MIYOUSHE_NEWS", {})
    game_choice = str(mode_settings.get("game") or content_cfg.get("game") or "GENSHIN").upper()

    # forum_id 映射：原神=28, 星穹铁道=53, 绝区零=58, 崩坏3=6, 综合大别野=34
    forum_map = {
        "GENSHIN": ("28", "原神"),
        "STAR_RAIL": ("53", "崩坏：星穹铁道"),
        "ZZZ": ("58", "绝区零"),
        "HONKAI3": ("6", "崩坏3"),
        "ALL": ("28", "米游社官方"),
    }
    forum_id, game_name = forum_map.get(game_choice, ("28", "原神"))
    cache_key = f"miyoushe_forum_{forum_id}"

    cached_data = None
    if cache_key in _MEDIA_CACHE:
        ts, items = _MEDIA_CACHE[cache_key]
        if now - ts < _CACHE_TTL and items:
            cached_data = items

    proxy = resolve_proxy_url(config.get("global_proxy_url"), auto_detect=True)
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

    if not cached_data:
        url = f"https://bbs-api.miyoushe.com/post/wapi/getForumPostList?forum_id={forum_id}&page_size=5&sort_type=1"
        try:
            async with httpx.AsyncClient(proxy=proxy, timeout=8.0, headers=headers) as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    data = resp.json()
                    cached_data = data.get("data", {}).get("list", [])
                    _MEDIA_CACHE[cache_key] = (now, cached_data)
        except Exception as exc:
            logger.warning("[GamingMedia] Failed to fetch Miyoushe news: %s", exc)

    if cached_data and len(cached_data) > 0:
        post_obj = cached_data[0].get("post", {})
        title = post_obj.get("subject", "")
        content = post_obj.get("content", "")
        images = post_obj.get("images", [])
        cover = images[0] if images else ""
        created_at = post_obj.get("created_at")
        date_str = time.strftime("%Y-%m-%d", time.localtime(created_at)) if created_at else "最新公告"

        res = dict(fallback)
        res.update({
            "game_badge": game_name,
            "title": title or fallback.get("title", f"{game_name}官方公告"),
            "category_tag": "官方活动 · 公告速递",
            "summary": _clean_text(content, 120) or fallback.get("summary", ""),
            "published_at": date_str,
            "cover_url": cover or fallback.get("cover_url", ""),
            "footer_label": f"MIYOUSHE · {game_name} 最新资讯",
        })
        return res

    return dict(fallback)


# ==========================================
# 5. 游民星空 单机资讯 (GAMERSKY_NEWS)
# ==========================================
@register_provider("gamersky_news")
async def generate_gamersky_news(
    mode_def: dict[str, Any],
    content_cfg: dict[str, Any],
    fallback: dict[str, Any],
    **kwargs: Any,
) -> dict[str, Any]:
    global _MEDIA_CACHE
    now = time.time()
    cache_key = "gamersky_news"

    cached_data = None
    if cache_key in _MEDIA_CACHE:
        ts, items = _MEDIA_CACHE[cache_key]
        if now - ts < _CACHE_TTL and items:
            cached_data = items

    config = kwargs.get("config") or {}
    proxy = resolve_proxy_url(config.get("global_proxy_url"), auto_detect=True)
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

    if not cached_data:
        try:
            async with httpx.AsyncClient(proxy=proxy, timeout=8.0, headers=headers) as client:
                resp = await client.get("https://www.gamersky.com/")
                if resp.status_code == 200:
                    html_text = resp.text
                    matches = re.findall(r'<a href="(https://www\.gamersky\.com/news/\d+/\d+\.shtml)"[^>]*>([^<]+)</a>', html_text)
                    items = []
                    for link, title in matches:
                        t = title.strip()
                        if len(t) >= 8 and not any(skip in t for skip in ("一碗", "甜品", "父亲", "网红")):
                            items.append({"title": t, "link": link})
                    cached_data = items
                    _MEDIA_CACHE[cache_key] = (now, cached_data)
        except Exception as exc:
            logger.warning("[GamingMedia] Failed to fetch Gamersky: %s", exc)

    if cached_data and len(cached_data) > 0:
        top_item = cached_data[0]
        res = dict(fallback)
        res.update({
            "header_tag": "游民星空 · 单机资讯",
            "title": top_item["title"],
            "source_tag": "GAMERSKY 单机动态",
            "summary": f"新作动态、游戏预告与前沿硬件情报实时追踪，最新大作评测一览无遗。",
            "published_at": "今日更新",
            "cover_url": "https://dummyimage.com/640x360/1a1a24/ffffff.png&text=GAMERSKY+NEWS",
            "footer_label": "GAMERSKY · 单机与主机最新动向",
        })
        return res

    return dict(fallback)


# ==========================================
# 6. 触乐 最新文章 (CHUAPP_ARTICLES)
# ==========================================
@register_provider("chuapp_articles")
async def generate_chuapp_articles(
    mode_def: dict[str, Any],
    content_cfg: dict[str, Any],
    fallback: dict[str, Any],
    **kwargs: Any,
) -> dict[str, Any]:
    global _MEDIA_CACHE
    now = time.time()
    cache_key = "chuapp_feed"

    cached_data = None
    if cache_key in _MEDIA_CACHE:
        ts, items = _MEDIA_CACHE[cache_key]
        if now - ts < _CACHE_TTL and items:
            cached_data = items

    config = kwargs.get("config") or {}
    proxy = resolve_proxy_url(config.get("global_proxy_url"), auto_detect=True)
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

    if not cached_data:
        try:
            async with httpx.AsyncClient(proxy=proxy, timeout=8.0, headers=headers) as client:
                resp = await client.get("https://www.chuapp.com/feed")
                if resp.status_code == 200:
                    root = ET.fromstring(resp.content)
                    raw_items = root.findall(".//item")
                    parsed = []
                    for it in raw_items[:6]:
                        title = it.find("title").text if it.find("title") is not None else ""
                        desc = it.find("description").text if it.find("description") is not None else ""
                        author = it.find("author").text if it.find("author") is not None else "触乐"
                        pub_date = it.find("pubDate").text if it.find("pubDate") is not None else ""
                        parsed.append({
                            "title": title.strip(),
                            "desc": _clean_text(desc, 130),
                            "author": author.strip() or "触乐特约作者",
                            "pub_date": pub_date[:16] if pub_date else "近期",
                        })
                    cached_data = parsed
                    _MEDIA_CACHE[cache_key] = (now, cached_data)
        except Exception as exc:
            logger.warning("[GamingMedia] Failed to fetch Chuapp feed: %s", exc)

    if cached_data and len(cached_data) > 0:
        art = cached_data[0]
        res = dict(fallback)
        res.update({
            "header_tag": "触乐 · 游戏人文故事",
            "title": art["title"],
            "author": art.get("author", "触乐编辑部"),
            "summary": art.get("desc", ""),
            "published_at": art.get("pub_date", "近期"),
            "quote": "记录游戏与人，寻找那些值得被记录的玩家故事。",
            "footer_label": "CHUAPP · 触乐网深度故事",
        })
        return res

    return dict(fallback)


# ==========================================
# 7. 游研社 最新文章 (YYSTV_ARTICLES)
# ==========================================
@register_provider("yystv_articles")
async def generate_yystv_articles(
    mode_def: dict[str, Any],
    content_cfg: dict[str, Any],
    fallback: dict[str, Any],
    **kwargs: Any,
) -> dict[str, Any]:
    global _MEDIA_CACHE
    now = time.time()
    cache_key = "yystv_feed"

    cached_data = None
    if cache_key in _MEDIA_CACHE:
        ts, items = _MEDIA_CACHE[cache_key]
        if now - ts < _CACHE_TTL and items:
            cached_data = items

    config = kwargs.get("config") or {}
    proxy = resolve_proxy_url(config.get("global_proxy_url"), auto_detect=True)
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

    if not cached_data:
        try:
            async with httpx.AsyncClient(proxy=proxy, timeout=8.0, headers=headers) as client:
                resp = await client.get("https://www.yystv.cn/rss/feed")
                if resp.status_code == 200:
                    root = ET.fromstring(resp.content)
                    raw_items = root.findall(".//item")
                    parsed = []
                    for it in raw_items[:6]:
                        title = it.find("title").text if it.find("title") is not None else ""
                        desc = it.find("description").text if it.find("description") is not None else ""
                        author = it.find("author").text if it.find("author") is not None else "游研社"
                        pub_date = it.find("pubDate").text if it.find("pubDate") is not None else ""
                        parsed.append({
                            "title": title.strip(),
                            "desc": _clean_text(desc, 130),
                            "author": author.strip() or "游研社",
                            "pub_date": pub_date[:16] if pub_date else "近期",
                        })
                    cached_data = parsed
                    _MEDIA_CACHE[cache_key] = (now, cached_data)
        except Exception as exc:
            logger.warning("[GamingMedia] Failed to fetch YYSTV feed: %s", exc)

    if cached_data and len(cached_data) > 0:
        art = cached_data[0]
        res = dict(fallback)
        res.update({
            "header_tag": "游研社 · 游戏社评与文化",
            "title": art["title"],
            "author": art.get("author", "游研社"),
            "summary": art.get("desc", ""),
            "published_at": art.get("pub_date", "近期"),
            "footer_label": "YYSTV · 游研社游戏故事与见闻",
        })
        return res

    return dict(fallback)
