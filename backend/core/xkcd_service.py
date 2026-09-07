"""
InkSight XKCD 每日极客漫画服务 (XKCD Daily Geek Comic Service)
抓取 XKCD 最新漫画，提取标题、幽默悬停注释 (alt text) 与图像，
并使用 Floyd-Steinberg 误差扩散算法将漫画优化为高对比度 1-bit 墨水屏二值图像。
"""
from __future__ import annotations

import asyncio
import io
import logging
import time
from typing import Any

from PIL import Image, ImageDraw

from .outbound_http import RequestPolicy, outbound_http
from .source_health import source_health

logger = logging.getLogger(__name__)

_XKCD_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}
_XKCD_CACHE_TTL = 3600.0 * 6  # 6 小时缓存


def _process_comic_image(img: Image.Image, max_w: int = 360, max_h: int = 180) -> Image.Image:
    """将漫画按比例等比缩放并应用 Floyd-Steinberg 抖动转换为 1-bit 墨水屏图像。"""
    w, h = img.size
    ratio = min(max_w / max(1, w), max_h / max(1, h), 1.0)
    new_w = max(1, int(w * ratio))
    new_h = max(1, int(h * ratio))

    resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
    # 灰度化然后进行误差扩散抖动
    return resized.convert("L").convert("1", dither=Image.Dither.FLOYDSTEINBERG)


def _get_fallback_comic() -> dict[str, Any]:
    """生成离线备用经典 XKCD 漫画 (Comic #927: Standards)。"""
    # 绘制一张经典极客漫画示意图
    img = Image.new("1", (320, 140), 1)
    d = ImageDraw.Draw(img)
    # 漫画边框与分格
    d.rectangle([(10, 10), (150, 130)], outline=0, width=1)
    d.rectangle([(160, 10), (310, 130)], outline=0, width=1)
    d.text((20, 20), "Situation:", fill=0)
    d.text((20, 36), "There are 14", fill=0)
    d.text((20, 52), "competing", fill=0)
    d.text((20, 68), "standards.", fill=0)
    # 火柴人
    d.ellipse([(110, 70), (120, 80)], outline=0, width=1)
    d.line([(115, 80), (115, 105)], fill=0, width=1)
    d.line([(105, 90), (125, 90)], fill=0, width=1)
    d.line([(115, 105), (108, 125)], fill=0, width=1)
    d.line([(115, 105), (122, 125)], fill=0, width=1)

    d.text((170, 20), "We need to", fill=0)
    d.text((170, 36), "develop ONE", fill=0)
    d.text((170, 52), "universal standard", fill=0)
    d.text((170, 68), "that covers all...", fill=0)
    d.text((170, 100), "Soon: 15 standards.", fill=0)

    return {
        "num": 927,
        "title": "Standards",
        "alt": "Fortunately, the charging one has been solved now that we've all standardized on mini-USB. Wait, micro-USB. No, wait, USB-C.",
        "date": "2026-09-07",
        "img_url": "https://imgs.xkcd.com/comics/standards.png",
        "comic_image": img,
        "source_status": "fallback",
    }


async def get_daily_xkcd(comic_num: int | None = None) -> dict[str, Any]:
    """抓取最新或指定编号的 XKCD 漫画并预处理为 1-bit 墨水屏图像。"""
    cache_key = f"xkcd:{comic_num or 'latest'}"
    now = time.time()

    cached = _XKCD_CACHE.get(cache_key)
    if cached and (now - cached[0] < _XKCD_CACHE_TTL):
        return dict(cached[1])

    if not source_health.should_allow_request("xkcd_api"):
        if cached:
            stale = dict(cached[1])
            stale["source_status"] = "stale"
            return stale
        return _get_fallback_comic()

    endpoint = f"https://xkcd.com/{comic_num}/info.0.json" if comic_num else "https://xkcd.com/info.0.json"
    policy = RequestPolicy(max_attempts=2, timeout=RequestPolicy().timeout)

    try:
        resp = await asyncio.to_thread(outbound_http.get_json, endpoint, policy=policy)
        if resp.status_code != 200:
            raise RuntimeError(f"XKCD API status {resp.status_code}")

        data = resp.json()
        img_url = data.get("img")
        if not img_url:
            raise ValueError("No comic image URL found")

        # Fetch image bytes
        img_resp = await asyncio.to_thread(outbound_http.get_text, img_url, policy=policy)
        raw_bytes = img_resp.content if hasattr(img_resp, "content") else img_resp.text.encode("latin1")

        with Image.open(io.BytesIO(raw_bytes)) as pil_img:
            processed_img = _process_comic_image(pil_img, max_w=360, max_h=180)

        year = data.get("year", "")
        month = data.get("month", "").zfill(2)
        day = data.get("day", "").zfill(2)
        date_str = f"{year}-{month}-{day}" if year else time.strftime("%Y-%m-%d")

        comic_data = {
            "num": data.get("num", 0),
            "title": data.get("safe_title") or data.get("title", "Comic"),
            "alt": data.get("alt", ""),
            "date": date_str,
            "img_url": img_url,
            "comic_image": processed_img,
            "source_status": "fresh",
        }

        source_health.record_success("xkcd_api")
        _XKCD_CACHE[cache_key] = (now, comic_data)
        return comic_data

    except Exception as exc:
        source_health.record_failure("xkcd_api", type(exc).__name__)
        logger.warning("[XKCDService] Failed to fetch live comic: %s", exc)
        if cached:
            stale = dict(cached[1])
            stale["source_status"] = "stale"
            return stale
        return _get_fallback_comic()
