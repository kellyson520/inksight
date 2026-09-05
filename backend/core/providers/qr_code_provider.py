"""
二维码模式数据提供者 (QR Code Mode Provider)
支持自定义文本、Wi-Fi 账号密码自动配网格式、电子名片或网址跳转。
"""
from __future__ import annotations

import logging
from typing import Any
from .base import register_provider

logger = logging.getLogger(__name__)


@register_provider("qr_code")
async def generate_qr_code(
    mode_def: dict[str, Any],
    content_cfg: dict[str, Any],
    fallback: dict[str, Any],
    **kwargs: Any,
) -> dict[str, Any]:
    """生成二维码展示模式的动态数据。"""
    config = kwargs.get("config") or {}
    overrides = config.get("mode_overrides", {}).get("QR_CODE", {})

    qr_type = overrides.get("type") or "URL"
    title = overrides.get("title") or "扫码直达"
    subtitle = overrides.get("subtitle") or "使用手机微信或相机扫一扫"
    footer_tip = overrides.get("footer_tip") or "InkSight 智能桌面助手"

    if qr_type == "WIFI":
        ssid = overrides.get("wifi_ssid", "InkSight-Guest")
        pwd = overrides.get("wifi_password", "")
        enc = overrides.get("wifi_encryption", "WPA")
        qr_content = f"WIFI:T:{enc};S:{ssid};P:{pwd};;"
        title = overrides.get("title") or "扫码连接 Wi-Fi"
        subtitle = f"无线网络: {ssid}"
        badge_text = "WI-FI 便捷联网"
    elif qr_type == "TEXT":
        qr_content = overrides.get("text", "Hello from InkSight!")
        badge_text = "纯文本展示"
    else:  # URL
        qr_content = overrides.get("url") or "https://github.com/kellyson520/inksight"
        badge_text = "网址快捷访问"

    date_ctx = kwargs.get("date_ctx") or {}
    return {
        "title": title,
        "subtitle": subtitle,
        "qr_content": qr_content,
        "badge_text": badge_text,
        "footer_tip": footer_tip,
        "update_time": date_ctx.get("time_str", "实时"),
    }
