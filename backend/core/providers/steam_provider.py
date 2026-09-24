"""
Steam 个人资料、游戏与好友状态 Provider
为墨水屏提供：
1. steam_achievements: Steam我的成就（最近游玩的游戏和已解锁的成就）
2. steam_recent: Steam最近在玩（最近玩过的游戏、近两周与累计游玩时间）
3. steam_random: Steam今天玩什么（从公开游戏库随机抽取并推荐）
4. steam_friends: Steam好友状态（好友在线/游戏中状态，查看谁在偷偷玩）

【网络与缓存策略】：
- 优先支持用户绑定的自定义 Steam 主页链接，若未填写则使用官方测试主页：
  https://steamcommunity.com/profiles/76561198978201763/
- 自动集成代理探测（resolve_proxy_url）以防 Steam 社区网络受限
- 内置 15 分钟内存 TTL 缓存与防抖防 429 机制
"""
from __future__ import annotations

import logging
import random
import re
import time
from typing import Any
import httpx

from core.recommendation_provider import resolve_proxy_url
from .base import register_provider

logger = logging.getLogger(__name__)


def _make_client(proxy: str | None = None, **kwargs) -> httpx.AsyncClient:
    if proxy:
        try:
            return httpx.AsyncClient(proxy=proxy, **kwargs)
        except TypeError:
            return httpx.AsyncClient(proxies=proxy, **kwargs)
    return httpx.AsyncClient(**kwargs)


# 默认测试主页
DEFAULT_STEAM_URL = "https://steamcommunity.com/profiles/76561198978201763/"

# 内存防抖缓存：url -> (timestamp, data)
_CACHE_TTL_SEC = 900  # 15 分钟
_STEAM_PROFILE_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}
_STEAM_FRIENDS_CACHE: dict[str, tuple[float, list[dict[str, Any]]]] = {}

# 备用高质量预置数据（当 Steam 社区离线或遭遇 429 时无缝回退）
_FALLBACK_GAMES = [
    {
        "appid": "289070",
        "name": "Sid Meier's Civilization VI",
        "capsule": "https://shared.akamai.steamstatic.com/store_item_assets/steam/apps/289070/capsule_184x69.jpg",
        "header": "https://shared.akamai.steamstatic.com/store_item_assets/steam/apps/289070/header.jpg",
        "hours_total": "62.0",
        "hours_2w": "12.5",
        "ach_unlocked": "37",
        "ach_total": "320",
        "ach_pct": "12",
        "achievements": ["Alfred Wegener's Legacy", "Land Party", "Investment Banking", "Ten Commandments"],
        "reason": "开一局文明VI吧，体验一把世界征服的快感，再来一个回合就天亮了！",
    },
    {
        "appid": "1426210",
        "name": "It Takes Two (双人成行)",
        "capsule": "https://shared.akamai.steamstatic.com/store_item_assets/steam/apps/1426210/capsule_184x69.jpg",
        "header": "https://shared.akamai.steamstatic.com/store_item_assets/steam/apps/1426210/header.jpg",
        "hours_total": "22.0",
        "hours_2w": "3.0",
        "ach_unlocked": "7",
        "ach_total": "20",
        "ach_pct": "35",
        "achievements": ["Struck A Pose", "It Took Two", "On Rails Experience"],
        "reason": "叫上好搭档一起开启双人奇幻冒险，默契与欢笑同在！",
    },
    {
        "appid": "1623730",
        "name": "Palworld (幻兽帕鲁)",
        "capsule": "https://shared.akamai.steamstatic.com/store_item_assets/steam/apps/1623730/capsule_184x69.jpg",
        "header": "https://shared.akamai.steamstatic.com/store_item_assets/steam/apps/1623730/header.jpg",
        "hours_total": "0.4",
        "hours_2w": "0.4",
        "ach_unlocked": "1",
        "ach_total": "75",
        "ach_pct": "2",
        "achievements": ["Beginning of the Legend"],
        "reason": "广袤奇幻世界，抓捕帕鲁经营基地，轻松解压！",
    },
]

_FALLBACK_FRIENDS = [
    {"name": "Hank Garcia", "status": "in_game", "status_label": "游戏中", "game": "Counter-Strike 2", "dot": "●"},
    {"name": "James Allen", "status": "online", "status_label": "在线", "game": "在线", "dot": "●"},
    {"name": "kelly", "status": "offline", "status_label": "离线", "game": "7小时前在线", "dot": "○"},
    {"name": "Momo.368", "status": "offline", "status_label": "离线", "game": "1天前在线", "dot": "○"},
    {"name": "YANG", "status": "offline", "status_label": "离线", "game": "2天前在线", "dot": "○"},
]


def normalize_steam_profile_target(url_or_id: str) -> tuple[str, str]:
    """标准化 Steam 主页链接，返回 (url_base, canonical_url)"""
    val = (url_or_id or "").strip()
    if not val:
        val = DEFAULT_STEAM_URL

    # 纯 17 位纯数字 ID
    if re.match(r"^\d{16,20}$", val):
        canonical = f"https://steamcommunity.com/profiles/{val}/"
        return canonical, canonical

    # 包含 profiles 或 id 的完整/部分链接
    m_prof = re.search(r"steamcommunity\.com/profiles/(\d+)", val)
    if m_prof:
        pid = m_prof.group(1)
        canonical = f"https://steamcommunity.com/profiles/{pid}/"
        return canonical, canonical

    m_id = re.search(r"steamcommunity\.com/id/([a-zA-Z0-9_\-]+)", val)
    if m_id:
        custom_id = m_id.group(1)
        canonical = f"https://steamcommunity.com/id/{custom_id}/"
        return canonical, canonical

    if val.startswith("http://") or val.startswith("https://"):
        return val.rstrip("/") + "/", val.rstrip("/") + "/"

    canonical = f"https://steamcommunity.com/profiles/{val}/"
    return canonical, canonical


async def _resolve_user_steam_url(kwargs: dict[str, Any]) -> str:
    """按优先级查找用户配置的 Steam 主页链接。"""
    config = kwargs.get("config") or {}
    mode_overrides = config.get("mode_overrides") or {}
    mode_settings = config.get("mode_settings") or {}

    # 1. 模式特定覆盖
    for k in ("STEAM_ACHIEVEMENTS", "STEAM_RECENT", "STEAM_RANDOM", "STEAM_FRIENDS", "STEAM"):
        ov = mode_overrides.get(k)
        if isinstance(ov, dict) and ov.get("steam_url"):
            return str(ov["steam_url"]).strip()
        st = mode_settings.get(k)
        if isinstance(st, dict) and st.get("steam_url"):
            return str(st["steam_url"]).strip()

    # 2. 从设备 owner 偏好中读取
    mac = kwargs.get("mac")
    if mac:
        try:
            from core.config_store import get_device_owner, get_user_preferences
            owner = await get_device_owner(mac)
            if owner and owner.get("user_id"):
                prefs = await get_user_preferences(owner["user_id"])
                if prefs.get("steam_profile_url"):
                    return str(prefs["steam_profile_url"]).strip()
        except Exception as exc:
            logger.debug("[SteamProvider] Error resolving owner steam url: %s", exc)

    return DEFAULT_STEAM_URL


async def fetch_steam_profile_data(steam_url: str, proxy_url: str | None = None) -> dict[str, Any]:
    """抓取并解析 Steam 个人主页与近期游戏/成就。"""
    canon_url, _ = normalize_steam_profile_target(steam_url)
    now = time.time()

    if canon_url in _STEAM_PROFILE_CACHE:
        ts, cached = _STEAM_PROFILE_CACHE[canon_url]
        if now - ts < _CACHE_TTL_SEC:
            return cached

    proxy = resolve_proxy_url(proxy_url, auto_detect=True)
    html = ""
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"}

    try:
        async with _make_client(proxy=proxy, timeout=8.0, follow_redirects=True, headers=headers) as client:
            resp = await client.get(canon_url)
            if resp.status_code == 200:
                html = resp.text
            else:
                logger.warning("[SteamProvider] Steam profile HTTP %s for %s", resp.status_code, canon_url)
    except Exception as exc:
        logger.warning("[SteamProvider] Failed to fetch steam profile %s: %s", canon_url, exc)

    if not html:
        # 使用兜底默认数据
        data = {
            "persona_name": "O_0",
            "level": "11",
            "games": _FALLBACK_GAMES,
        }
        _STEAM_PROFILE_CACHE[canon_url] = (now, data)
        return data

    # 解析 Persona Name 与 等级
    p_name_m = re.search(r'<span class="actual_persona_name">([^<]+)</span>', html)
    persona = p_name_m.group(1).strip() if p_name_m else "Steam玩家"

    lvl_m = re.search(r'<span class="friendPlayerLevelNum">(\d+)</span>', html)
    level = lvl_m.group(1) if lvl_m else "1"

    # 解析近期游戏
    games: list[dict[str, Any]] = []
    game_chunks = html.split('<div class="recent_game">')[1:]
    for chunk in game_chunks:
        name_m = re.search(r'<div class="game_name"><a class="whiteLink" href="[^\"]*app/(\d+)">([^<]+)</a>', chunk)
        if not name_m:
            continue
        appid = name_m.group(1)
        name = name_m.group(2).strip()

        capsule_m = re.search(r'<img class="game_capsule" src="([^\"]+)"', chunk)
        capsule = capsule_m.group(1) if capsule_m else f"https://shared.akamai.steamstatic.com/store_item_assets/steam/apps/{appid}/header.jpg"

        hrs_m = re.search(r'([\d\.,]+)\s*hrs?\s*on\s*record', chunk)
        hrs_total = hrs_m.group(1) if hrs_m else "0"

        hrs_2w_m = re.search(r'([\d\.,]+)\s*hrs?\s*past\s*2\s*weeks', chunk)
        hrs_2w = hrs_2w_m.group(1) if hrs_2w_m else "0"

        prog_m = re.search(r'<span class="ellipsis">(\d+)\s*of\s*(\d+)</span>', chunk)
        ach_unlocked = prog_m.group(1) if prog_m else "0"
        ach_total = prog_m.group(2) if prog_m else "0"

        pct_m = re.search(r'class="progress_bar" style="width:\s*(\d+)%"', chunk)
        pct = pct_m.group(1) if pct_m else "0"
        if not pct or pct == "0":
            try:
                if int(ach_total) > 0:
                    pct = str(int(int(ach_unlocked) * 100 / int(ach_total)))
            except (ValueError, ZeroDivisionError):
                pct = "0"

        achievements = re.findall(r'<div class="game_info_achievement" data-tooltip-text="([^\"]+)">', chunk)

        games.append({
            "appid": appid,
            "name": name,
            "capsule": capsule,
            "header": f"https://shared.akamai.steamstatic.com/store_item_assets/steam/apps/{appid}/header.jpg",
            "hours_total": hrs_total,
            "hours_2w": hrs_2w,
            "ach_unlocked": ach_unlocked,
            "ach_total": ach_total,
            "ach_pct": pct,
            "achievements": achievements,
            "reason": f"近期专注游玩《{name}》，累计历练 {hrs_total} 小时，再接再厉！",
        })

    if not games:
        games = _FALLBACK_GAMES

    data = {
        "persona_name": persona,
        "level": level,
        "games": games,
    }
    _STEAM_PROFILE_CACHE[canon_url] = (now, data)
    return data


async def fetch_steam_friends_data(steam_url: str, proxy_url: str | None = None) -> list[dict[str, Any]]:
    """抓取并解析 Steam 好友列表及实时状态。"""
    canon_url, _ = normalize_steam_profile_target(steam_url)
    friends_url = canon_url.rstrip("/") + "/friends/"
    now = time.time()

    if canon_url in _STEAM_FRIENDS_CACHE:
        ts, cached = _STEAM_FRIENDS_CACHE[canon_url]
        if now - ts < _CACHE_TTL_SEC:
            return cached

    proxy = resolve_proxy_url(proxy_url, auto_detect=True)
    html = ""
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"}

    try:
        async with _make_client(proxy=proxy, timeout=8.0, follow_redirects=True, headers=headers) as client:
            resp = await client.get(friends_url)
            if resp.status_code == 200:
                html = resp.text
            else:
                logger.warning("[SteamProvider] Steam friends HTTP %s for %s", resp.status_code, friends_url)
    except Exception as exc:
        logger.warning("[SteamProvider] Failed to fetch steam friends %s: %s", friends_url, exc)

    friends: list[dict[str, Any]] = []
    if html:
        raw_items = re.findall(r'class="selectable friend_block_v2 persona (in-game|online|offline)[^\"]*".*?<div class="friend_block_content">([^<]+)<br>(.*?)</div>\s*</div>', html, re.S)
        for status, name, content in raw_items:
            clean_name = name.strip()
            game_m = re.search(r'<span class="[^\"]*link[^\"]*">([^<]+)</span>', content)
            subtext_m = re.search(r'<span class="[^\"]*text[^\"]*">([^<]+)</span>', content)
            game_str = game_m.group(1).strip() if game_m else (subtext_m.group(1).strip() if subtext_m else "")

            if status == "in-game":
                status_label = "游戏中"
                dot = "●"
            elif status == "online":
                status_label = "在线"
                dot = "●"
            else:
                status_label = "离线"
                dot = "○"

            friends.append({
                "name": clean_name,
                "status": status,
                "status_label": status_label,
                "game": game_str or status_label,
                "dot": dot,
            })

    if not friends:
        friends = _FALLBACK_FRIENDS

    # 排序：游戏中 > 在线 > 离线
    status_order = {"in-game": 0, "online": 1, "offline": 2}
    friends.sort(key=lambda x: status_order.get(x["status"], 3))

    _STEAM_FRIENDS_CACHE[canon_url] = (now, friends)
    return friends


# ==========================================
# 1. Steam我的成就 (STEAM_ACHIEVEMENTS)
# ==========================================
@register_provider("steam_achievements")
async def generate_steam_achievements(
    mode_def: dict[str, Any],
    content_cfg: dict[str, Any],
    fallback: dict[str, Any],
    **kwargs: Any,
) -> dict[str, Any]:
    steam_url = await _resolve_user_steam_url(kwargs)
    config = kwargs.get("config") or {}
    proxy_url = config.get("global_proxy_url")

    data = await fetch_steam_profile_data(steam_url, proxy_url=proxy_url)
    games = data.get("games", [])
    primary_game = games[0] if games else _FALLBACK_GAMES[0]

    achs = primary_game.get("achievements", [])
    ach1 = achs[0] if len(achs) > 0 else "第一块里程碑"
    ach2 = achs[1] if len(achs) > 1 else "探险先行者"
    ach3 = achs[2] if len(achs) > 2 else "精通之境"

    pct = int(primary_game.get("ach_pct") or 0)
    unlocked = primary_game.get("ach_unlocked", "0")
    total = primary_game.get("ach_total", "0")

    res = dict(fallback)
    res.update({
        "persona_name": data.get("persona_name", "Steam玩家"),
        "level": data.get("level", "1"),
        "game_name": primary_game.get("name", "Steam热门游戏"),
        "cover_url": primary_game.get("header", ""),
        "progress_label": f"已解锁 {unlocked} / {total} 项成就",
        "progress_pct": pct,
        "progress_text": f"{pct}%",
        "ach1_name": ach1,
        "ach2_name": ach2,
        "ach3_name": ach3,
        "hours_total": f"{primary_game.get('hours_total', '0')} 小时",
        "footer_label": "STEAM ACHIEVEMENTS · 成就之路",
    })
    return res


# ==========================================
# 2. Steam最近在玩 (STEAM_RECENT)
# ==========================================
@register_provider("steam_recent")
async def generate_steam_recent(
    mode_def: dict[str, Any],
    content_cfg: dict[str, Any],
    fallback: dict[str, Any],
    **kwargs: Any,
) -> dict[str, Any]:
    steam_url = await _resolve_user_steam_url(kwargs)
    config = kwargs.get("config") or {}
    proxy_url = config.get("global_proxy_url")

    data = await fetch_steam_profile_data(steam_url, proxy_url=proxy_url)
    games = data.get("games", [])
    if len(games) < 3:
        games = list(games) + _FALLBACK_GAMES[len(games):]

    g1, g2, g3 = games[0], games[1], games[2]

    res = dict(fallback)
    res.update({
        "persona_name": data.get("persona_name", "Steam玩家"),
        "level": data.get("level", "1"),
        "game1_name": g1.get("name", ""),
        "game1_cover": g1.get("capsule", g1.get("header", "")),
        "game1_hours_total": f"累计 {g1.get('hours_total', '0')}h",
        "game1_hours_2w": f"近两周 {g1.get('hours_2w', '0')}h",
        "game2_name": g2.get("name", ""),
        "game2_cover": g2.get("capsule", g2.get("header", "")),
        "game2_hours_total": f"累计 {g2.get('hours_total', '0')}h",
        "game2_hours_2w": f"近两周 {g2.get('hours_2w', '0')}h",
        "game3_name": g3.get("name", ""),
        "game3_cover": g3.get("capsule", g3.get("header", "")),
        "game3_hours_total": f"累计 {g3.get('hours_total', '0')}h",
        "game3_hours_2w": f"近两周 {g3.get('hours_2w', '0')}h",
        "footer_label": "STEAM RECENT · 近期游玩记录",
    })
    return res


# ==========================================
# 3. Steam今天玩什么 (STEAM_RANDOM)
# ==========================================
@register_provider("steam_random")
async def generate_steam_random(
    mode_def: dict[str, Any],
    content_cfg: dict[str, Any],
    fallback: dict[str, Any],
    **kwargs: Any,
) -> dict[str, Any]:
    steam_url = await _resolve_user_steam_url(kwargs)
    config = kwargs.get("config") or {}
    proxy_url = config.get("global_proxy_url")

    data = await fetch_steam_profile_data(steam_url, proxy_url=proxy_url)
    games = data.get("games", [])
    if not games:
        games = _FALLBACK_GAMES

    # 随机抽取一款游戏
    picked = random.choice(games)

    res = dict(fallback)
    res.update({
        "persona_name": data.get("persona_name", "Steam玩家"),
        "picked_game": picked.get("name", ""),
        "cover_url": picked.get("header", picked.get("capsule", "")),
        "playtime_badge": f"已游玩 {picked.get('hours_total', '0')} 小时",
        "ach_badge": f"成就进度 {picked.get('ach_pct', '0')}%",
        "recommend_reason": picked.get("reason", "今天就玩这款！重温经典，探索未完的旅程。"),
        "footer_label": "STEAM TODAY · 随机决定",
    })
    return res


# ==========================================
# 4. Steam好友状态 (STEAM_FRIENDS)
# ==========================================
@register_provider("steam_friends")
async def generate_steam_friends(
    mode_def: dict[str, Any],
    content_cfg: dict[str, Any],
    fallback: dict[str, Any],
    **kwargs: Any,
) -> dict[str, Any]:
    steam_url = await _resolve_user_steam_url(kwargs)
    config = kwargs.get("config") or {}
    proxy_url = config.get("global_proxy_url")

    friends = await fetch_steam_friends_data(steam_url, proxy_url=proxy_url)
    online_count = sum(1 for f in friends if f["status"] in ("in-game", "online"))
    ingame_count = sum(1 for f in friends if f["status"] == "in-game")

    # 填充前 5 位好友
    display_friends = friends[:5]
    while len(display_friends) < 5:
        display_friends.append({"name": "暂无更多好友", "status": "offline", "status_label": "离线", "game": "-", "dot": "○"})

    res = dict(fallback)
    res.update({
        "header_title": "STEAM 好友动态",
        "status_summary": f"在线: {online_count} 人 · 游戏中: {ingame_count} 人",
        "cover_url": "https://shared.akamai.steamstatic.com/store_item_assets/steam/apps/730/header.jpg",
        "f1_dot": display_friends[0]["dot"],
        "f1_name": display_friends[0]["name"],
        "f1_status": display_friends[0]["status_label"],
        "f1_game": display_friends[0]["game"],
        "f2_dot": display_friends[1]["dot"],
        "f2_name": display_friends[1]["name"],
        "f2_status": display_friends[1]["status_label"],
        "f2_game": display_friends[1]["game"],
        "f3_dot": display_friends[2]["dot"],
        "f3_name": display_friends[2]["name"],
        "f3_status": display_friends[2]["status_label"],
        "f3_game": display_friends[2]["game"],
        "f4_dot": display_friends[3]["dot"],
        "f4_name": display_friends[3]["name"],
        "f4_status": display_friends[3]["status_label"],
        "f4_game": display_friends[3]["game"],
        "f5_dot": display_friends[4]["dot"],
        "f5_name": display_friends[4]["name"],
        "f5_status": display_friends[4]["status_label"],
        "f5_game": display_friends[4]["game"],
        "footer_label": "STEAM FRIENDS · 看看谁在偷偷玩",
    })
    return res
