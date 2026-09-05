"""
InkSight 原生二维码渲染 Block (QR Code Block)
支持自定义文本/URL内容、错误纠正等级(L/M/Q/H)、像素大小、边框padding与反色。
专为墨水屏 1-bit 高对比度像素对齐优化，避免缩放模糊。
"""
from __future__ import annotations

import logging
from typing import Any
from PIL import Image, ImageDraw
import qrcode
from qrcode.constants import ERROR_CORRECT_L, ERROR_CORRECT_M, ERROR_CORRECT_Q, ERROR_CORRECT_H

from core.patterns.utils import EINK_BG, EINK_FG
from .context import RenderContext
from .registry import register_block

logger = logging.getLogger(__name__)

_CORRECTION_MAP = {
    "L": ERROR_CORRECT_L,
    "M": ERROR_CORRECT_M,
    "Q": ERROR_CORRECT_Q,
    "H": ERROR_CORRECT_H,
}


@register_block("qrcode")
def render_qrcode(ctx: RenderContext, block: dict) -> None:
    """在墨水屏画布上渲染高对比度矢量对齐二维码。"""
    field_name = block.get("field", "qr_content")
    text = str(ctx.get_field(field_name) if field_name else "")
    if not text:
        text = str(ctx.resolve(block.get("template", block.get("text", "https://inksight.local"))))

    if not text:
        return

    size = int(block.get("size", 140) * ctx.scale)
    border = int(block.get("border", 1))
    correction_str = str(block.get("correction", "M")).upper()
    error_correction = _CORRECTION_MAP.get(correction_str, ERROR_CORRECT_M)
    invert = bool(block.get("invert", False))
    margin_x = int(block.get("margin_x", 0) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 6) * ctx.scale)
    align = str(block.get("align", "center")).lower()

    qr = qrcode.QRCode(
        version=None,
        error_correction=error_correction,
        box_size=1,
        border=border,
    )
    qr.add_data(text)
    qr.make(fit=True)

    # 得到 1-bit 二值图像
    qr_img = qr.make_image(fill_color="black", back_color="white").convert("1")

    # 使用 NEAREST 插值放大到目标像素大小，保证每个 QR 像素块边缘绝对清晰锐利
    qr_resized = qr_img.resize((size, size), Image.NEAREST)

    if invert:
        # 反色
        qr_resized = qr_resized.point(lambda p: 255 if p == 0 else 0, mode="1")

    # 计算水平对齐
    if align == "left":
        x = ctx.x_offset + margin_x
    elif align == "right":
        x = ctx.x_offset + ctx.available_width - size - margin_x
    else:  # center
        x = ctx.x_offset + margin_x + max(0, (ctx.available_width - margin_x * 2 - size) // 2)

    y = ctx.y

    # 粘贴至画布 (使用 paste_icon 保持调色板及透明通道安全)
    if ctx.colors >= 3:
        ctx.img.paste(qr_resized, (x, y))
    else:
        ctx.paste_icon(qr_resized, (x, y))

    ctx.y = y + size + margin_bottom
