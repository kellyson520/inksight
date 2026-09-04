"""
渲染核心上下文与通用工具 (Render Context & Contracts)
定义所有 Block 渲染器共用的 RenderContext 数据契约、颜色映射与模板解析。
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any

from PIL import Image, ImageDraw

from core.config import (
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
    EINK_COLOR_NAME_MAP,
    EINK_COLOR_AVAILABILITY,
)
from core.patterns.utils import EINK_BG, EINK_FG, paste_icon_onto

logger = logging.getLogger(__name__)

STATUS_BAR_BOTTOM_DEFAULT = 36

_EMOJI_PATTERN = re.compile(
    r"[\U0001F300-\U0001F9FF\u2600-\u26FF\u2700-\u27BF]+", re.UNICODE
)

_LABEL_EMOJI_TO_ICON = {
    "\U0001f4d6": "book",
    "\U0001f4a1": "tips",
    "\U0001f31f": "star",
}


def strip_emoji(s: str) -> str:
    """去除中文字体通常不支持的 Emoji 字符。"""
    if not s:
        return s
    return _EMOJI_PATTERN.sub("", s).strip()


def section_icon_from_label(label: str) -> str | None:
    """若标签包含常见 Emoji，映射为对应的内置矢量图标名。"""
    for emoji, icon_name in _LABEL_EMOJI_TO_ICON.items():
        if label.startswith(emoji) or emoji in label:
            return icon_name
    return None


def resolve_template(content: dict, template: str) -> str:
    """递归/正则替换字符串中的 {field} 占位符。"""
    def _replace(m: re.Match) -> str:
        key = m.group(1)
        val = content.get(key, "")
        if isinstance(val, list):
            return ", ".join(str(v) for v in val)
        return str(val)
    return re.sub(r"\{(\w+)\}", _replace, template)


@dataclass
class RenderContext:
    """贯穿整个 JSON 渲染树的可变状态上下文。"""
    draw: ImageDraw.ImageDraw
    img: Image.Image
    content: dict
    screen_w: int = SCREEN_WIDTH
    screen_h: int = SCREEN_HEIGHT
    y: int = STATUS_BAR_BOTTOM_DEFAULT
    x_offset: int = 0
    available_width: int = SCREEN_WIDTH
    footer_height: int = 30
    colors: int = 2
    footer_top_offset: int = 0

    @property
    def scale(self) -> float:
        return max(0.92, self.screen_w / 400.0)

    @property
    def h_scale(self) -> float:
        return self.screen_h / 300.0

    @property
    def min_scale(self) -> float:
        """基于宽高的保守缩放比率。"""
        return max(0.65, min(self.scale, self.h_scale))

    def __post_init__(self):
        if self.available_width == SCREEN_WIDTH and self.screen_w != SCREEN_WIDTH:
            self.available_width = self.screen_w

    @property
    def footer_top(self) -> int:
        return self.screen_h - self.footer_height + self.footer_top_offset

    def resolve(self, template: str) -> str:
        """解析 {field} 占位符。"""
        return resolve_template(self.content, template)

    def get_field(self, name: str) -> Any:
        return self.content.get(name, "")

    @property
    def remaining_height(self) -> int:
        return self.footer_top - self.y

    def color_index(self, name: str, default: int = EINK_FG) -> int:
        """根据当前墨水屏色彩深度返回调色板索引（黑白或多色）。"""
        available = EINK_COLOR_AVAILABILITY.get(self.colors, frozenset())
        if name not in available:
            return default
        return EINK_COLOR_NAME_MAP.get(name, default)

    def resolve_color(self, block: dict, default: int = EINK_FG) -> int:
        """解析 block 中的 'color' 属性。"""
        name = block.get("color")
        if not name:
            return default
        return self.color_index(name, default)

    def paste_icon(self, icon: Image.Image, pos: tuple[int, int], fill: int = EINK_FG) -> None:
        """将 1-bit 图标粘贴到画布上，妥善处理透明度和调色板模式。"""
        paste_icon_onto(self.img, icon, pos, fill)


def resolve_named_color(ctx: RenderContext, color_name: Any, default: int = EINK_FG) -> int:
    if not isinstance(color_name, str) or not color_name:
        return default
    return ctx.color_index(color_name, default)
