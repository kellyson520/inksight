"""
渲染器模块
负责将内容渲染为墨水屏图像，并提供统一的模式分发接口

STOIC, ROAST, ZEN, FITNESS, POETRY 已迁移至 JSON 渲染引擎 (json_renderer.py)。
此处仅分发尚未迁移的 Python 内置模式。
"""

from __future__ import annotations

import io
from PIL import Image

from .config import SCREEN_WIDTH, SCREEN_HEIGHT
from .patterns import render_error

__all__ = [
    "render_error",
    "render_mode",
    "image_to_bmp_bytes",
    "image_to_png_bytes",
    "image_to_raw_2bpp",
]


def render_mode(
    persona: str,
    content: dict,
    *,
    date_str: str,
    weather_str: str,
    battery_pct: float,
    weather_code: int = -1,
    time_str: str = "",
    date_ctx: dict | None = None,
    screen_w: int = SCREEN_WIDTH,
    screen_h: int = SCREEN_HEIGHT,
) -> Image.Image:
    """Legacy dispatcher retained for backward compatibility.

    All production modes are JSON-defined and rendered by json_renderer.
    """
    raise ValueError(
        f"Unknown builtin persona '{persona}'. "
        "JSON-defined modes should be routed through json_renderer."
    )


def image_to_bmp_bytes(img: Image.Image) -> bytes:
    """将图像转换为 BMP 字节流"""
    buf = io.BytesIO()
    img.save(buf, format="BMP")
    return buf.getvalue()


def image_to_raw_2bpp(img: Image.Image) -> bytes:
    """Convert image to raw 2bpp packed bytes for 4-color e-ink.

    Pixel mapping: 0=black, 1=white, 2=yellow, 3=red.
    4 pixels packed per byte, MSB first (bits 7-6 = first pixel).
    Row-major, top to bottom.
    """
    w, h = img.size
    expected_len = w * h // 4

    try:
        import numpy as np
        if img.mode == "1":
            arr = (np.array(img, dtype=np.uint8) != 0).astype(np.uint8)
        else:
            if img.mode != "P":
                img = img.convert("P")
            arr = np.array(img, dtype=np.uint8) & 0x03

        pad_w = (4 - (w % 4)) % 4
        if pad_w:
            arr = np.pad(arr, ((0, 0), (0, pad_w)), mode="constant", constant_values=1)

        px = arr.reshape(-1, 4)
        packed = (px[:, 0] << 6) | (px[:, 1] << 4) | (px[:, 2] << 2) | px[:, 3]
        return packed.tobytes()[:expected_len]
    except Exception:
        # Graceful pure-Python fallback
        if img.mode == "1":
            pixels = img.load()
            out = bytearray(expected_len)
            idx = 0
            for y in range(h):
                for x in range(0, w, 4):
                    packed = 0
                    for bit in range(4):
                        px = x + bit
                        is_white = pixels[px, y] if px < w else 1
                        color = 0x01 if is_white else 0x00
                        packed |= color << (6 - bit * 2)
                    if idx < expected_len:
                        out[idx] = packed
                        idx += 1
            return bytes(out)

        if img.mode != "P":
            img = img.convert("P")
        pixels = img.load()
        out = bytearray(expected_len)
        idx = 0
        for y in range(h):
            for x in range(0, w, 4):
                packed = 0
                for bit in range(4):
                    px = x + bit
                    color = (pixels[px, y] & 0x03) if px < w else 0x01
                    packed |= color << (6 - bit * 2)
                if idx < expected_len:
                    out[idx] = packed
                    idx += 1
        return bytes(out)


def image_to_png_bytes(img: Image.Image) -> bytes:
    """将图像转换为 PNG 字节流"""
    if img.mode == "1":
        img = img.convert("L")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
