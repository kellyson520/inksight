"""
游戏折扣与限免活动 Provider (Game Discount & Epic Giveaway Provider)
为墨水屏提供：
1. xiaoheihe_discount: 小黑盒游戏折扣信息，随机展示一款正在优惠的游戏。
2. epic_free: 查看Epic喜加一活动，快速了解当前或下一期的免费游戏。
"""
from __future__ import annotations

import json
import logging
import random
import time
from pathlib import Path
from typing import Any
import httpx

from core.recommendation_provider import resolve_proxy_url
from .base import register_provider

logger = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
_DISCOUNT_CACHE_FILE = _DATA_DIR / "game_discounts_cache.json"
_EPIC_CACHE_FILE = _DATA_DIR / "epic_free_cache.json"

_CACHE_TTL = 1800  # 30 分钟缓存
_DISCOUNT_CACHE: dict[str, tuple[float, list[dict[str, Any]]]] = {}
_EPIC_CACHE: tuple[float, list[dict[str, Any]]] = (0.0, [])


def _load_json_disk_cache(path: Path) -> Any | None:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        logger.debug("[GameDiscount] Read disk cache failed: %s", e)
    return None


def _save_json_disk_cache(path: Path, data: Any) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        logger.debug("[GameDiscount] Write disk cache failed: %s", e)


def _make_client(proxy: str | None = None, **kwargs) -> httpx.AsyncClient:
    if proxy:
        try:
            return httpx.AsyncClient(proxy=proxy, **kwargs)
        except TypeError:
            return httpx.AsyncClient(proxies=proxy, **kwargs)
    return httpx.AsyncClient(**kwargs)

_FALLBACK_DISCOUNTS = [
    {
        "game_name": "双人成行 (It Takes Two)",
        "discount_badge": "-70%",
        "original_price": "¥198.00",
        "current_price": "¥59.40",
        "cut_price": "直降 ¥138.60",
        "historical_status": "平史低",
        "rating_label": "好评如潮 (95%)",
        "deadline_label": "Steam 周期特惠",
        "tag_list": "合作 · 动作 · 冒险",
        "cover_url": "https://shared.akamai.steamstatic.com/store_item_assets/steam/apps/1426210/header_schinese.jpg",
        "description": "年度最佳游戏，突破常理的奇幻合作冒险之旅，两名玩家必须齐心协力方能化险为夷。",
    },
    {
        "game_name": "双影奇境 (Split Fiction)",
        "discount_badge": "-35%",
        "original_price": "¥198.00",
        "current_price": "¥128.70",
        "cut_price": "立省 ¥69.30",
        "historical_status": "新史低",
        "rating_label": "特别好评 (88%)",
        "deadline_label": "限时特惠中",
        "tag_list": "解谜 · 科幻 · 唯美",
        "cover_url": "https://shared.akamai.steamstatic.com/store_item_assets/steam/apps/2001120/header.jpg",
        "description": "双重视角空间折叠解谜，极富艺术感的次世代视觉盛宴与情感交织故事。",
    },
    {
        "game_name": "空之轨迹 the 2nd",
        "discount_badge": "-10%",
        "original_price": "¥298.00",
        "current_price": "¥268.20",
        "cut_price": "立省 ¥29.80",
        "historical_status": "首发折扣",
        "rating_label": "好评如潮 (97%)",
        "deadline_label": "新品特惠",
        "tag_list": "JRPG · 经典重制 · 剧情",
        "cover_url": "https://shared.akamai.steamstatic.com/store_item_assets/steam/apps/4225980/7e2f29dcf817ea28698ed1e27f4b86c98ebf1aa3/header_schinese.jpg",
        "description": "游击士艾丝蒂尔与约修亚的传奇续篇，全面进化的画质与动人旋律重温感动。",
    },
    {
        "game_name": "机械狂欢 (Mechanical Party)",
        "discount_badge": "-20%",
        "original_price": "¥33.00",
        "current_price": "¥26.40",
        "cut_price": "立省 ¥6.60",
        "historical_status": "平史低",
        "rating_label": "多半好评 (76%)",
        "deadline_label": "周末狂欢",
        "tag_list": "休闲 · 聚会 · 派对",
        "cover_url": "https://shared.akamai.steamstatic.com/store_item_assets/steam/apps/4108000/bf97e80547a68eac1ad2c481c2f64b6e276d5801/header_schinese.jpg",
        "description": "支持最多 8 人同屏互坑欢乐派对游戏，欢声笑语停不下来。",
    },
]

_FALLBACK_EPIC_GAMES = [
    {
        "game_title": "《幽灵行者 2》",
        "status_label": "本周免费",
        "original_price": "原价 ¥169.00",
        "deadline_label": "截止 09月26日 23:00",
        "cover_url": "https://dummyimage.com/640x360/1a1a24/ffffff.png&text=GHOSTRUNNER+II",
        "description": "第一人称赛博朋克砍杀动作游戏，在毁灭后的达摩塔外荒原展开高速跑酷与激烈斩击！",
        "claim_url": "https://store.epicgames.com/",
    },
    {
        "game_title": "《LISA: 决定版》",
        "status_label": "下周预告",
        "original_price": "原价 ¥108.00",
        "deadline_label": "09月27日 开启领取",
        "cover_url": "https://dummyimage.com/640x360/222222/ffffff.png&text=LISA+DEFINITIVE",
        "description": "废土末世风格的荒诞黑色幽默横版 RPG，充满艰难抉择与深刻人性拷问。",
        "claim_url": "https://store.epicgames.com/",
    },
]


async def fetch_game_discounts(proxy_url: str | None = None) -> list[dict[str, Any]]:
    """获取热门游戏特惠列表（Steam Specials 简体中文源）。"""
    global _DISCOUNT_CACHE
    now = time.time()
    cache_key = "steam_specials_cn"

    if cache_key in _DISCOUNT_CACHE:
        ts, cached = _DISCOUNT_CACHE[cache_key]
        if now - ts < _CACHE_TTL and cached:
            return cached

    proxy = resolve_proxy_url(proxy_url, auto_detect=True)
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    url = "https://store.steampowered.com/api/featuredcategories/?l=schinese&cc=cn"

    specials_list: list[dict[str, Any]] = []
    try:
        async with _make_client(proxy=proxy, timeout=8.0, follow_redirects=True, headers=headers) as client:
            resp = await client.get(url)
            if resp.status_code == 200:
                data = resp.json()
                raw_items = data.get("specials", {}).get("items", [])
                for it in raw_items:
                    name = it.get("name")
                    if not name:
                        continue
                    pct = it.get("discount_percent", 0)
                    if pct <= 0:
                        continue
                    orig_cents = it.get("original_price", 0)
                    final_cents = it.get("final_price", 0)
                    orig_yuan = orig_cents / 100.0
                    final_yuan = final_cents / 100.0
                    cut_yuan = orig_yuan - final_yuan

                    header_img = it.get("header_image") or f"https://shared.cloudflare.steamstatic.com/store_item_assets/steam/apps/{it.get('id')}/header.jpg"

                    specials_list.append({
                        "game_name": name,
                        "discount_badge": f"-{pct}%",
                        "original_price": f"¥{orig_yuan:.2f}".rstrip("0").rstrip(".") if not orig_yuan.is_integer() else f"¥{int(orig_yuan)}",
                        "current_price": f"¥{final_yuan:.2f}".rstrip("0").rstrip(".") if not final_yuan.is_integer() else f"¥{int(final_yuan)}",
                        "cut_price": f"立省 ¥{cut_yuan:.1f}".rstrip("0").rstrip("."),
                        "historical_status": "新史低" if pct >= 50 else "限时特惠",
                        "rating_label": "特惠中",
                        "deadline_label": "Steam 热门特惠",
                        "tag_list": "小黑盒热搜折扣",
                        "cover_url": header_img,
                        "description": f"热门大作限时特惠中，折后价格极具性价比，抓紧时间入手！",
                    })
    except Exception as exc:
        logger.warning("[GameDiscountProvider] Failed to fetch Steam specials: %s", exc)

    if specials_list:
        _save_json_disk_cache(_DISCOUNT_CACHE_FILE, specials_list)
    else:
        disk_specials = _load_json_disk_cache(_DISCOUNT_CACHE_FILE)
        if disk_specials and isinstance(disk_specials, list) and len(disk_specials) > 0:
            specials_list = disk_specials
        else:
            specials_list = _FALLBACK_DISCOUNTS

    _DISCOUNT_CACHE[cache_key] = (now, specials_list)
    return specials_list


async def fetch_epic_free_games(proxy_url: str | None = None) -> list[dict[str, Any]]:
    """获取 Epic Games 免费游戏（优先官方 API，备选 GamerPower）。"""
    global _EPIC_CACHE
    now = time.time()
    ts, cached = _EPIC_CACHE
    if now - ts < _CACHE_TTL and cached:
        return cached

    proxy = resolve_proxy_url(proxy_url, auto_detect=True)
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    epic_url = "https://store-site-backend-static-ipv4.ak.epicgames.com/freeGamesPromotions?locale=zh-CN&country=CN&allowCountries=CN"

    free_games: list[dict[str, Any]] = []

    try:
        async with _make_client(proxy=proxy, timeout=8.0, follow_redirects=True, headers=headers) as client:
            resp = await client.get(epic_url)
            if resp.status_code == 200:
                data = resp.json()
                elements = data.get("data", {}).get("Catalog", {}).get("searchStore", {}).get("elements", [])
                for el in elements:
                    promotions = el.get("promotions") or {}
                    offers = promotions.get("promotionalOffers") or []
                    upcoming = promotions.get("upcomingPromotionalOffers") or []

                    if not offers and not upcoming:
                        continue

                    title = el.get("title", "")
                    desc = el.get("description", "")
                    orig_price = el.get("price", {}).get("totalPrice", {}).get("fmtPrice", {}).get("originalPrice", "免费")

                    # 提取最佳比例封面
                    key_images = el.get("keyImages", [])
                    cover = ""
                    for img_obj in key_images:
                        if img_obj.get("type") in ("DieselStoreFrontWide", "OfferImageWide", "Thumbnail"):
                            cover = img_obj.get("url", "")
                            break
                    if not cover and key_images:
                        cover = key_images[0].get("url", "")

                    if offers:
                        status_label = "本周免费"
                        deadline_info = "限时领取中"
                        try:
                            end_time = offers[0].get("promotionalOffers", [])[0].get("endDate", "")[:10]
                            if end_time:
                                deadline_info = f"截止 {end_time}"
                        except Exception:
                            pass
                    else:
                        status_label = "下周预告"
                        deadline_info = "即将推出"
                        try:
                            start_time = upcoming[0].get("promotionalOffers", [])[0].get("startDate", "")[:10]
                            if start_time:
                                deadline_info = f"{start_time} 开放"
                        except Exception:
                            pass

                    free_games.append({
                        "game_title": title,
                        "status_label": status_label,
                        "original_price": f"原价 {orig_price}" if not str(orig_price).startswith("原价") else str(orig_price),
                        "deadline_label": deadline_info,
                        "cover_url": cover,
                        "description": desc or "Epic Games 本期精选限免大作，一键入库，终身畅玩！",
                        "claim_url": "https://store.epicgames.com/",
                    })
    except Exception as exc:
        logger.warning("[GameDiscountProvider] Failed to fetch official Epic free games: %s", exc)

    # 备用 GamerPower
    if not free_games:
        try:
            gp_url = "https://www.gamerpower.com/api/giveaways?platform=epic-games-store"
            async with _make_client(proxy=proxy, timeout=6.0, follow_redirects=True, headers=headers) as client:
                resp = await client.get(gp_url)
                if resp.status_code == 200:
                    data = resp.json()
                    for item in data[:5]:
                        free_games.append({
                            "game_title": item.get("title", "Epic 免费游戏"),
                            "status_label": "限时免费",
                            "original_price": f"原价 {item.get('worth', '$14.99')}",
                            "deadline_label": f"截止 {str(item.get('end_date', ''))[:10]}" if item.get("end_date") else "限时领取",
                            "cover_url": item.get("image", item.get("thumbnail", "")),
                            "description": item.get("description", "Epic Games 限时免费领！"),
                            "claim_url": item.get("open_giveaway_url", "https://store.epicgames.com/"),
                        })
        except Exception as exc:
            logger.warning("[GameDiscountProvider] Failed to fetch GamerPower Epic: %s", exc)

    if free_games:
        _save_json_disk_cache(_EPIC_CACHE_FILE, free_games)
    else:
        disk_epic = _load_json_disk_cache(_EPIC_CACHE_FILE)
        if disk_epic and isinstance(disk_epic, list) and len(disk_epic) > 0:
            free_games = disk_epic
        else:
            free_games = _FALLBACK_EPIC_GAMES

    _EPIC_CACHE = (now, free_games)
    return free_games


# ==========================================
# 1. 小黑盒 游戏折扣 (XIAOHEIHE_DISCOUNT)
# ==========================================
@register_provider("xiaoheihe_discount")
async def generate_xiaoheihe_discount(
    mode_def: dict[str, Any],
    content_cfg: dict[str, Any],
    fallback: dict[str, Any],
    **kwargs: Any,
) -> dict[str, Any]:
    config = kwargs.get("config") or {}
    proxy_url = config.get("global_proxy_url")

    discounts = await fetch_game_discounts(proxy_url=proxy_url)
    picked = random.choice(discounts) if discounts else _FALLBACK_DISCOUNTS[0]

    res = dict(fallback)
    res.update({
        "header_title": "小黑盒 · 热门折扣",
        "game_name": picked.get("game_name", ""),
        "discount_badge": picked.get("discount_badge", "-50%"),
        "current_price": picked.get("current_price", "¥0"),
        "original_price": picked.get("original_price", "¥0"),
        "cut_price": picked.get("cut_price", "特惠立减"),
        "historical_status": picked.get("historical_status", "平史低"),
        "rating_label": picked.get("rating_label", "特别好评"),
        "deadline_label": picked.get("deadline_label", "特惠进行中"),
        "tag_list": picked.get("tag_list", "游戏特惠"),
        "cover_url": picked.get("cover_url", ""),
        "description": picked.get("description", "小黑盒游戏特惠推荐，折后超值！"),
        "footer_label": "XIAOHEIHE · 游戏好价每日选",
    })
    return res


# ==========================================
# 2. Epic喜加一 (EPIC_FREE)
# ==========================================
@register_provider("epic_free")
async def generate_epic_free(
    mode_def: dict[str, Any],
    content_cfg: dict[str, Any],
    fallback: dict[str, Any],
    **kwargs: Any,
) -> dict[str, Any]:
    config = kwargs.get("config") or {}
    proxy_url = config.get("global_proxy_url")

    free_games = await fetch_epic_free_games(proxy_url=proxy_url)
    primary = free_games[0] if free_games else _FALLBACK_EPIC_GAMES[0]

    res = dict(fallback)
    res.update({
        "header_title": "EPIC GAMES · 喜加一",
        "game_title": primary.get("game_title", "免费游戏"),
        "status_label": primary.get("status_label", "限时免费"),
        "original_price": primary.get("original_price", "免费"),
        "deadline_label": primary.get("deadline_label", "限免领取中"),
        "cover_url": primary.get("cover_url", ""),
        "description": primary.get("description", "本周 Epic Games 限时免费领取大作，一键入库终身畅玩！"),
        "claim_url": primary.get("claim_url", "https://store.epicgames.com/"),
        "footer_label": "EPIC FREE GAMES · 喜加一活动",
    })
    return res
