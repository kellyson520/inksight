"""
InkSight 固件分发与版本管理服务 (Firmware Management Service)
负责 GitHub Releases 固件检测、资产包展开、芯片架构识别 (ESP32 / ESP32-C3 / ESP32-S3)、清单生成与固件 URL 可用性验证。
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from typing import Any, Optional
from urllib.parse import urlparse

import httpx

logger = logging.getLogger(__name__)

FIRMWARE_CHIP_FAMILY = "ESP32-C3"
FIRMWARE_RELEASE_CACHE_TTL = int(os.getenv("FIRMWARE_RELEASE_CACHE_TTL", "120"))
GITHUB_OWNER = os.getenv("GITHUB_OWNER", "datascale-ai")
GITHUB_REPO = os.getenv("GITHUB_REPO", "inksight")
GITHUB_RELEASES_API = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases"

_firmware_release_cache: dict[str, Any] = {
    "expires_at": 0.0,
    "payload": None,
}
_firmware_release_cache_lock = asyncio.Lock()


def build_firmware_manifest(
    version: str, download_url: str, chip_family: str = FIRMWARE_CHIP_FAMILY
) -> dict[str, Any]:
    return {
        "name": "InkSight",
        "version": version,
        "builds": [
            {
                "chipFamily": chip_family,
                "parts": [{"path": download_url, "offset": 0}],
            }
        ],
    }


def chip_family_from_asset_name(asset_name: str) -> str:
    name = (asset_name or "").lower()
    if "_s3" in name or "esp32s3" in name or "esp32-s3" in name:
        return "ESP32-S3"
    if "wroom32e" in name or "_esp32" in name:
        return "ESP32"
    if "_c3" in name or "esp32c3" in name:
        return "ESP32-C3"
    return FIRMWARE_CHIP_FAMILY


def pick_firmware_asset(assets: list[dict[str, Any]]) -> Optional[dict[str, Any]]:
    preferred = [
        asset
        for asset in assets
        if asset.get("name", "").endswith(".bin")
        and "inksight-firmware-" in asset.get("name", "")
    ]
    if preferred:
        return preferred[0]
    fallback = [asset for asset in assets if asset.get("name", "").endswith(".bin")]
    return fallback[0] if fallback else None


def expand_firmware_release_assets(release: dict[str, Any]) -> list[dict[str, Any]]:
    tag_name = release.get("tag_name", "")
    version = tag_name.lstrip("v") if tag_name else "unknown"
    published_at = release.get("published_at")
    items = []
    for asset in release.get("assets", []):
        asset_name = asset.get("name", "")
        if not asset_name.endswith(".bin"):
            continue
        download_url = asset.get("browser_download_url")
        if not download_url:
            continue
        chip_family = chip_family_from_asset_name(asset_name)
        items.append(
            {
                "version": version,
                "tag": tag_name,
                "published_at": published_at,
                "download_url": download_url,
                "size_bytes": asset.get("size"),
                "chip_family": chip_family,
                "asset_name": asset_name,
                "manifest": build_firmware_manifest(version, download_url, chip_family),
            }
        )
    preferred = [item for item in items if "inksight-firmware-" in item["asset_name"]]
    return preferred or items


async def load_firmware_releases(force_refresh: bool = False) -> dict[str, Any]:
    now = time.time()
    async with _firmware_release_cache_lock:
        if (
            not force_refresh
            and _firmware_release_cache["payload"] is not None
            and _firmware_release_cache["expires_at"] > now
        ):
            cached_payload = dict(_firmware_release_cache["payload"])
            cached_payload["cached"] = True
            return cached_payload

        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "inksight-firmware-api",
        }
        github_token = os.getenv("GITHUB_TOKEN")
        if github_token:
            headers["Authorization"] = f"Bearer {github_token}"

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(GITHUB_RELEASES_API, headers=headers)
        if resp.status_code >= 400:
            message = f"GitHub releases API error: {resp.status_code}"
            try:
                details = resp.json().get("message")
                if details:
                    message = f"{message} - {details}"
            except (ValueError, TypeError, json.JSONDecodeError):
                logger.warning("[FIRMWARE] Failed to parse GitHub error payload", exc_info=True)
            raise RuntimeError(message)

        releases = []
        for release in resp.json():
            if release.get("draft"):
                continue
            releases.extend(expand_firmware_release_assets(release))

        payload = {
            "source": "github_releases",
            "repo": f"{GITHUB_OWNER}/{GITHUB_REPO}",
            "cached": False,
            "count": len(releases),
            "releases": releases,
        }
        _firmware_release_cache["payload"] = payload
        _firmware_release_cache["expires_at"] = now + FIRMWARE_RELEASE_CACHE_TTL
        return payload


async def validate_firmware_url(url: str) -> dict[str, Any]:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("firmware URL must start with http:// or https://")
    if not parsed.netloc:
        raise ValueError("firmware URL host is missing")
    if not parsed.path.lower().endswith(".bin"):
        raise ValueError("firmware URL should point to a .bin file")

    async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
        try:
            resp = await client.head(url)
        except httpx.HTTPError:
            logger.warning("[FIRMWARE] HEAD failed for %s, falling back to ranged GET", url, exc_info=True)
            resp = await client.get(url, headers={"Range": "bytes=0-0"})
    if resp.status_code >= 400:
        raise RuntimeError(f"firmware URL is not reachable: {resp.status_code}")

    return {
        "ok": True,
        "reachable": True,
        "status_code": resp.status_code,
        "final_url": str(resp.url),
        "content_type": resp.headers.get("content-type"),
        "content_length": resp.headers.get("content-length"),
    }
