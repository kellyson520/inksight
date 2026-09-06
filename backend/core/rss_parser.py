from __future__ import annotations

import html
import logging
import re
import asyncio
import time
import xml.etree.ElementTree as ET
from typing import Any, Optional
from urllib.parse import urljoin

import httpx

from .outbound_http import RequestPolicy, outbound_http
from .source_result import SourceResult

logger = logging.getLogger(__name__)

# 内存缓存：URL -> (timestamp, data_dict)
_RSS_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}
_RSS_CACHE_TTL = 300  # 5分钟缓存


def _clean_html_text(raw_html: str, max_length: int = 180) -> str:
    """从 HTML 文本中提取干净的纯文本摘要。"""
    if not raw_html:
        return ""
    # 解码 HTML 实体
    text = html.unescape(raw_html)
    # 替换常见的换行标签
    text = re.sub(r"<(br|p|div|h[1-6]|li)[^>]*>", " ", text, flags=re.IGNORECASE)
    # 移除所有标签
    text = re.sub(r"<[^>]+>", "", text)
    # 压缩连续空白字符
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > max_length:
        return text[:max_length].rstrip() + "..."
    return text


def _extract_image_url(item_elem: ET.Element, description_html: str, base_url: str = "") -> str:
    """提取文章条目中的封面配图或第一张有效图片。"""
    # 1. 检查 <enclosure> 标签
    enclosure = item_elem.find("enclosure")
    if enclosure is not None:
        enc_type = enclosure.attrib.get("type", "")
        enc_url = enclosure.attrib.get("url", "")
        if enc_url and (not enc_type or enc_type.startswith("image/")):
            return urljoin(base_url, enc_url)

    # 2. 检查 media:content 或 media:thumbnail (带命名空间)
    for elem in item_elem.iter():
        tag_lower = elem.tag.lower()
        if "content" in tag_lower or "thumbnail" in tag_lower:
            url = elem.attrib.get("url", "")
            medium = elem.attrib.get("medium", "")
            if url and (medium == "image" or not medium or any(url.lower().endswith(ext) for ext in (".jpg", ".jpeg", ".png", ".webp", ".gif"))):
                return urljoin(base_url, url)

    # 3. 从 description / content:encoded 的 HTML 中寻找 <img>
    if description_html:
        img_matches = re.findall(r'<img[^>]+src=["\']([^"\']+)["\']', description_html, flags=re.IGNORECASE)
        for img_src in img_matches:
            # 过滤掉 1x1 追踪像素或表情图标
            if "icon" in img_src.lower() or "badge" in img_src.lower() or "spacer" in img_src.lower():
                continue
            return urljoin(base_url, img_src)

    return ""


async def fetch_rss_source(feed_url: str, timeout: float = 12.0) -> SourceResult[dict[str, Any]]:
    """Fetch RSS/Atom data using the shared SourceResult stale-if-error contract."""
    feed_url = feed_url.strip()
    if not feed_url:
        return SourceResult.fallback({"error": "Empty feed URL", "items": []}, source=feed_url, reason="empty_url")

    now = time.time()
    cached = _RSS_CACHE.get(feed_url)
    if cached and (now - cached[0] < _RSS_CACHE_TTL):
        return SourceResult.fresh(dict(cached[1]), source=feed_url, ttl_seconds=_RSS_CACHE_TTL)

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 InkSight/1.0",
        "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, */*",
    }
    try:
        base_timeout = RequestPolicy().timeout
        policy = RequestPolicy(
            timeout=httpx.Timeout(connect=base_timeout.connect, read=max(1.0, timeout), write=base_timeout.write, pool=base_timeout.pool),
            max_attempts=3,
            max_response_bytes=2 * 1024 * 1024,
            verify=True,
            follow_redirects=False,
        )
        response = await asyncio.to_thread(outbound_http.get_text, feed_url, headers=headers, policy=policy)
        raw_xml = response.text
    except Exception as exc:
        logger.warning("[RSS] Network error fetching %s: %s", feed_url, type(exc).__name__)
        if cached:
            return SourceResult(data=dict(cached[1]), source=feed_url, source_status="stale", error=type(exc).__name__)
        return SourceResult.fallback({"error": str(exc), "items": []}, source=feed_url, reason=type(exc).__name__)

    if not raw_xml:
        if cached:
            return SourceResult(data=dict(cached[1]), source=feed_url, source_status="stale", error="empty response")
        return SourceResult.fallback({"error": "Empty response", "items": []}, source=feed_url, reason="empty response")

    parsed = parse_rss_xml(raw_xml, base_url=feed_url)
    if parsed and parsed.get("items"):
        _RSS_CACHE[feed_url] = (now, parsed)
        return SourceResult.fresh(parsed, source=feed_url, ttl_seconds=_RSS_CACHE_TTL)
    reason = parsed.get("error", "empty feed") if parsed else "empty feed"
    if cached:
        return SourceResult(data=dict(cached[1]), source=feed_url, source_status="stale", error=reason)
    return SourceResult.fallback(parsed or {"error": "unavailable", "items": []}, source=feed_url, reason=reason)


async def fetch_and_parse_rss(feed_url: str, timeout: float = 12.0) -> dict[str, Any]:
    """Backward-compatible dict adapter for :func:`fetch_rss_source`."""
    result = await fetch_rss_source(feed_url, timeout=timeout)
    payload = dict(result.data)
    payload["source_status"] = result.source_status
    if result.error:
        payload["error"] = result.error
    return payload


def parse_rss_xml(raw_xml: str, base_url: str = "") -> dict[str, Any]:
    """解析 RSS/Atom 格式 XML 文本。"""
    try:
        root = ET.fromstring(raw_xml.strip())
    except ET.ParseError as e:
        logger.warning(f"[RSS] XML parse error: {e}")
        return {"error": f"Invalid XML: {e}", "items": []}

    tag = root.tag.lower()
    feed_title = ""
    feed_link = ""
    feed_desc = ""
    items: list[dict[str, Any]] = []

    # 1. Atom 格式 (feed -> entry)
    if "feed" in tag or root.tag.endswith("feed"):
        feed_title = (root.findtext("{http://www.w3.org/2005/Atom}title") or root.findtext("title") or "").strip()
        link_elem = root.find("{http://www.w3.org/2005/Atom}link") or root.find("link")
        if link_elem is not None:
            feed_link = link_elem.attrib.get("href", "") or link_elem.text or ""
        subtitle = root.findtext("{http://www.w3.org/2005/Atom}subtitle") or root.findtext("subtitle") or ""
        feed_desc = _clean_html_text(subtitle, 80)

        entries = root.findall(".//{http://www.w3.org/2005/Atom}entry") or root.findall(".//entry")
        for entry in entries:
            title = ""
            for e in entry.iter():
                if e.tag.endswith("title") and e.text:
                    title = e.text.strip()
                    break

            link = ""
            item_link_elem = entry.find("{http://www.w3.org/2005/Atom}link") or entry.find("link")
            if item_link_elem is not None:
                link = item_link_elem.attrib.get("href", "") or item_link_elem.text or ""

            raw_desc = ""
            for e in entry.iter():
                if (e.tag.endswith("summary") or e.tag.endswith("content")) and e.text:
                    raw_desc = e.text.strip()
                    break

            author = ""
            for elem in entry.iter():
                if elem.tag.endswith("name") and elem.text:
                    author = elem.text.strip()
                    break

            pub_date = (entry.findtext("{http://www.w3.org/2005/Atom}published") or entry.findtext("{http://www.w3.org/2005/Atom}updated") or entry.findtext("published") or entry.findtext("updated") or "").strip()

            image_url = _extract_image_url(entry, raw_desc, base_url)
            summary = _clean_html_text(raw_desc, 140)
            short_date = pub_date[:10] if pub_date else ""

            items.append({
                "title": title,
                "summary": summary,
                "link": link,
                "author": author,
                "date": short_date,
                "image_url": image_url,
            })

    # 2. 标准 RSS 2.0 / RSS 1.0 (channel -> item)
    else:
        channel = root.find("channel")
        ch = channel if channel is not None else root
        feed_title = (ch.findtext("title") or "").strip()
        feed_link = (ch.findtext("link") or "").strip()
        feed_desc = _clean_html_text(ch.findtext("description") or "", 80)

        raw_items = root.findall(".//item")
        for it in raw_items:
            title = (it.findtext("title") or "").strip()
            link = (it.findtext("link") or "").strip()
            raw_desc = it.findtext("description") or ""
            author = (it.findtext("author") or it.findtext("{http://purl.org/dc/elements/1.1/}creator") or "").strip()
            pub_date = (it.findtext("pubDate") or "").strip()

            content_encoded = it.findtext("{http://purl.org/rss/1.0/modules/content/}encoded") or ""
            desc_for_image = content_encoded or raw_desc
            image_url = _extract_image_url(it, desc_for_image, base_url)
            summary = _clean_html_text(raw_desc or content_encoded, 140)
            short_date = pub_date[:16] if pub_date else ""

            items.append({
                "title": title,
                "summary": summary,
                "link": link,
                "author": author,
                "date": short_date,
                "image_url": image_url,
            })

    return {
        "title": feed_title or "RSS Feed",
        "link": feed_link,
        "description": feed_desc,
        "items": items,
    }


def get_rss_item_content(parsed_feed: dict[str, Any], index: int = 0) -> dict[str, Any]:
    """提取单篇用于墨水屏展示的格式化字典。"""
    feed_title = parsed_feed.get("title") or "RSS Feed"
    items = parsed_feed.get("items") or []

    if not items:
        error_msg = parsed_feed.get("error") or "暂无文章或源解析失败"
        return {
            "feed_title": feed_title,
            "title": "暂无内容",
            "summary": error_msg,
            "author": "",
            "date": "",
            "image_url": "",
            "has_image": False,
            "total_items": 0,
            "current_index": 0,
        }

    idx = max(0, min(index, len(items) - 1))
    target = items[idx]

    img = target.get("image_url") or ""
    return {
        "feed_title": feed_title[:24],
        "title": target.get("title") or "无标题",
        "summary": target.get("summary") or "",
        "author": target.get("author") or "",
        "date": target.get("date") or "",
        "image_url": img,
        "has_image": bool(img),
        "total_items": len(items),
        "current_index": idx + 1,
    }
