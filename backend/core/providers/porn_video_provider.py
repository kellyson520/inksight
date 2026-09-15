"""Public Pornhub recommendation adapter; no login or access-control bypass."""
from __future__ import annotations
import asyncio
from typing import Any
import httpx
from PIL import Image, ImageDraw, ImageFilter
from ..outbound_http import RequestPolicy, outbound_http
from ..patterns.utils import load_font
from ..recommendation_provider import normalize_recommendation_item, resolve_proxy_url
from .base import register_provider

_DEFAULT_ENDPOINT = "https://www.pornhub.com/webmasters/search?thumbsize=large"
_FALLBACK_COVER = "https://images.unsplash.com/photo-1518709268805-4e9042af9f23?w=800&q=80"


def _format_duration(val: Any) -> str:
    if not val:
        return ""
    if isinstance(val, str) and ":" in val:
        return val.strip()
    try:
        sec = int(float(val))
        m, s = divmod(sec, 60)
        h, m = divmod(m, 60)
        if h > 0:
            return f"{h:02d}:{m:02d}:{s:02d}"
        return f"{m:02d}:{s:02d}"
    except (ValueError, TypeError):
        return str(val)


def _format_views(val: Any) -> str:
    if not val:
        return ""
    try:
        v = float(val)
        if v >= 100000000:
            formatted = f"{v / 100000000:.1f}".rstrip("0").rstrip(".")
            return f"{formatted}亿"
        if v >= 10000:
            formatted = f"{v / 10000:.1f}".rstrip("0").rstrip(".")
            return f"{formatted}万"
        if v >= 1000:
            formatted = f"{v / 1000:.1f}".rstrip("0").rstrip(".")
            return f"{formatted}k"
        return str(int(v))
    except (ValueError, TypeError):
        s = str(val).strip()
        return s


def _format_rating(val: Any) -> str:
    if not val:
        return ""
    try:
        r = float(val)
        return f"{int(round(r))}%"
    except (ValueError, TypeError):
        return f"{val}%" if "%" not in str(val) else str(val)


def _build_video_fallback_image(
    title: str = "精选推荐视频",
    author: str = "Official",
    duration: str = "14:28",
    views_label: str = "128万次播放",
    rating_label: str = "98%好评",
    rank_label: str = "NO.1",
    width: int = 640,
    height: int = 360,
) -> Image.Image:
    """Render an iwara-styled e-ink video card: sharp foreground cover on enlarged blurred backdrop."""
    # 1. 仿照 iwara：背后是扩大的放大镜式视频散焦毛玻璃模糊效果
    bg = Image.new("RGB", (width, height), (18, 18, 24))
    bg_draw = ImageDraw.Draw(bg)
    bg_draw.ellipse([-int(width * 0.1), -int(height * 0.2), int(width * 0.6), int(height * 0.9)], fill=(85, 45, 95))
    bg_draw.ellipse([int(width * 0.4), -int(height * 0.1), int(width * 1.15), int(height * 0.85)], fill=(110, 65, 30))
    bg_draw.ellipse([int(width * 0.15), int(height * 0.35), int(width * 0.85), int(height * 1.15)], fill=(35, 65, 90))
    bg_blurred = bg.filter(ImageFilter.GaussianBlur(radius=max(14, int(min(width, height) * 0.08))))
    image = bg_blurred
    draw = ImageDraw.Draw(image)

    # 2. 前置主体视频封面（中心微立体浮雕与高对比度边框）
    pad_x = int(width * 0.05)
    pad_y = int(height * 0.05)
    card_w = width - pad_x * 2
    card_h = height - pad_y * 2
    card_rect = [pad_x, pad_y, pad_x + card_w, pad_y + card_h]

    # 外层柔和发光/阴影
    draw.rounded_rectangle([pad_x - 3, pad_y - 3, pad_x + card_w + 3, pad_y + card_h + 3], radius=14, outline=(255, 255, 255, 60), width=1)
    # 前景封面主体
    draw.rounded_rectangle(card_rect, radius=12, fill=(26, 26, 32), outline=(230, 230, 235), width=2)

    # 3. 顶部左侧：P-HUB 标志性品牌徽章
    badge_x, badge_y = pad_x + 16, pad_y + 16
    draw.rounded_rectangle([badge_x, badge_y, badge_x + 138, badge_y + 42], radius=8, fill=(16, 16, 20))
    badge_font = load_font("noto_serif_bold", 22)
    draw.text((badge_x + 10, badge_y + 6), "PORN", fill=(255, 255, 255), font=badge_font)
    draw.rounded_rectangle([badge_x + 82, badge_y + 5, badge_x + 130, badge_y + 37], radius=5, fill=(255, 153, 0))
    draw.text((badge_x + 86, badge_y + 6), "HUB", fill=(0, 0, 0), font=badge_font)

    # 4. 顶部右侧：排名标签 (例如 NO.1)
    if rank_label:
        rank_font = load_font("noto_serif_bold", 20)
        draw.rounded_rectangle([pad_x + card_w - 100, badge_y, pad_x + card_w - 16, badge_y + 40], radius=8, fill=(240, 240, 245))
        draw.text((pad_x + card_w - 88, badge_y + 7), rank_label, fill=(20, 20, 25), font=rank_font)

    # 5. 画面正中心：微立体视频播放大按钮 (Play Circle)
    cx, cy = width // 2, height // 2 - 4
    r = min(card_w, card_h) // 6
    draw.ellipse([cx - r - 2, cy - r - 2, cx + r + 2, cy + r + 2], fill=(12, 12, 16), outline=(255, 255, 255, 160), width=2)
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(24, 24, 28), outline=(255, 153, 0), width=4)
    tri_w = int(r * 0.6)
    tri_h = int(r * 0.75)
    tri = [(cx - tri_w // 2 + 3, cy - tri_h // 2), (cx - tri_w // 2 + 3, cy + tri_h // 2), (cx + tri_w // 2 + 6, cy)]
    draw.polygon(tri, fill=(255, 255, 255))

    # 6. 底部右侧：高对比度时长标签 (Duration Badge, 如 14:28)
    tag_font = load_font("noto_serif_bold", 20)
    if duration:
        dur_text = duration if ":" in duration else f"{duration}"
        dur_w = max(80, int(len(dur_text) * 13 + 24))
        draw.rounded_rectangle([pad_x + card_w - dur_w - 16, pad_y + card_h - 52, pad_x + card_w - 16, pad_y + card_h - 16], radius=8, fill=(16, 16, 20), outline=(255, 255, 255, 100), width=1)
        draw.text((pad_x + card_w - dur_w - 4, pad_y + card_h - 46), dur_text, fill=(255, 255, 255), font=tag_font)

    # 7. 底部左侧：播放量与好评率徽章 (如 128万次播放 · 98%好评)
    info_parts = []
    if views_label:
        info_parts.append(f"▶ {views_label}")
    if rating_label:
        info_parts.append(f"★ {rating_label}")
    if info_parts:
        info_str = "  ".join(info_parts)
        info_font = load_font("noto_serif_regular", 18)
        info_w = int(len(info_str) * 11 + 30)
        draw.rounded_rectangle([pad_x + 16, pad_y + card_h - 52, min(pad_x + card_w - 140, pad_x + 16 + info_w), pad_y + card_h - 16], radius=8, fill=(240, 242, 246))
        draw.text((pad_x + 26, pad_y + card_h - 44), info_str, fill=(25, 25, 30), font=info_font)

    return image


def _local_fallback_image() -> Image.Image:
    return _build_video_fallback_image(
        title="P站精选视频推荐",
        author="Verified",
        duration="14:28",
        views_label="128万次播放",
        rating_label="98%好评",
        rank_label="NO.1",
    )


_FALLBACK = [
    {
        "title": "P站公开视频推荐",
        "subtitle": "精选公开热门",
        "source": "P站",
        "rank_label": "推荐",
        "duration": "14:28",
        "views_label": "128万次播放",
        "rating_label": "98%好评",
        "cover_url": _FALLBACK_COVER,
        "thumbnail_url": _FALLBACK_COVER,
        "image_data": _local_fallback_image(),
    }
]


def _parse_porn_items(payload: Any) -> list[dict[str, Any]]:
    raw = payload.get("videos", payload.get("data", payload)) if isinstance(payload, dict) else payload
    if not isinstance(raw, list):
        return []
    result = []
    for index, item in enumerate(raw[:10], 1):
        if not isinstance(item, dict):
            continue
        thumbs = item.get("thumbs") or []
        thumb_url = item.get("default_thumb") or (thumbs[0].get("src") if thumbs and isinstance(thumbs[0], dict) else "")
        title = item.get("title") or f"热门视频 #{index}"
        author = item.get("username") or item.get("uploader") or "P站"
        duration_str = _format_duration(item.get("duration"))
        views_str = _format_views(item.get("views"))
        rating_str = _format_rating(item.get("rating"))
        rank_str = f"NO.{index}"

        # 预先为视频条目生成精美微立体带播放器封面的矢量卡片，保障离线与弱网环境的高质感显示
        generated_cover = _build_video_fallback_image(
            title=title,
            author=author,
            duration=duration_str,
            views_label=f"{views_str}播放" if views_str else "",
            rating_label=f"{rating_str}好评" if rating_str else "",
            rank_label=rank_str,
        )

        result.append(
            normalize_recommendation_item(
                {
                    "title": title,
                    "subtitle": author,
                    "thumbnail": thumb_url or item.get("thumbnail") or item.get("thumb"),
                    "detail_url": item.get("url"),
                    "rank_label": rank_str,
                    "duration": duration_str,
                    "views_label": views_str,
                    "rating_label": rating_str,
                    "fallback_image": generated_cover,
                },
                source="P站",
            )
        )
    return result


@register_provider("porn_video")
async def generate_porn_video(mode_def, content_cfg, fallback, **kwargs):
    config = kwargs.get("config") or {}
    override = config.get("mode_overrides", {}).get("PORN_VIDEO", {})
    if not isinstance(override, dict):
        override = {}
    settings = config.get("mode_settings") or {}
    endpoint = override.get("endpoint") or settings.get("endpoint") or content_cfg.get("endpoint") or _DEFAULT_ENDPOINT
    proxy_url = resolve_proxy_url(config.get("global_proxy_url"), auto_detect=True)
    items = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
    }
    try:
        policy = RequestPolicy(
            timeout=httpx.Timeout(connect=2.5, read=5.0, write=3.0, pool=2.5),
            max_attempts=1 if not proxy_url else 2,
            follow_redirects=True,
        )
        response = await asyncio.to_thread(
            outbound_http.get_json,
            endpoint,
            headers=headers,
            proxy_url=proxy_url,
            policy=policy,
        )
        items = _parse_porn_items(response.json())
    except Exception:
        pass
    return {
        "title": "P站视频推荐",
        "source": "P站",
        "items": items or _FALLBACK,
        "layout_style": override.get("layout_style", "cover_card"),
    }
