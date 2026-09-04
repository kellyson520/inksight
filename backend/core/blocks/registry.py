"""
组件与块渲染器注册表 (Block Renderer Registry)
提供统一的块注册与调度分发，各领域渲染子模块按需注册。
"""
from __future__ import annotations

import logging
from typing import Any, Callable

from .context import RenderContext

logger = logging.getLogger(__name__)

# 全局块渲染器注册字典
BLOCK_RENDERERS: dict[str, Callable[[RenderContext, dict], None]] = {}


def register_block(btype: str, fn: Callable[[RenderContext, dict], None] | None = None):
    """注册一种 Block 渲染器。支持函数调用与装饰器两种模式。"""
    if fn is not None:
        BLOCK_RENDERERS[btype] = fn
        return fn

    def decorator(func: Callable[[RenderContext, dict], None]):
        BLOCK_RENDERERS[btype] = func
        return func

    return decorator


def render_block(ctx: RenderContext, block: dict) -> None:
    """分发渲染单个 Block。"""
    btype = block.get("type")
    if not btype:
        return
    renderer = BLOCK_RENDERERS.get(btype)
    if renderer:
        renderer(ctx, block)
    else:
        logger.debug("[JsonRenderer] Unknown block type: %s", btype)
