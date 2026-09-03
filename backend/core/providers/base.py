"""
Provider 插件注册中心
将多样化的开放数据源解耦为独立的微模块，支持快速扩充、独立测试与维护。
"""
from __future__ import annotations

import logging
from typing import Any, Awaitable, Callable, Optional

logger = logging.getLogger(__name__)

ProviderFunc = Callable[..., Awaitable[dict[str, Any]]]

_REGISTRY: dict[str, ProviderFunc] = {}


def register_provider(name: str):
    """装饰器：注册一个计算型/开放数据源 Provider。"""
    def decorator(fn: ProviderFunc) -> ProviderFunc:
        _REGISTRY[name.lower()] = fn
        return fn
    return decorator


async def dispatch_provider(
    name: str,
    mode_def: dict[str, Any],
    content_cfg: dict[str, Any],
    fallback: dict[str, Any],
    **kwargs: Any,
) -> Optional[dict[str, Any]]:
    """分发给注册的 Provider 执行。若未注册则返回 None。"""
    fn = _REGISTRY.get(name.lower())
    if not fn:
        return None
    try:
        return await fn(mode_def, content_cfg, fallback, **kwargs)
    except Exception as exc:
        logger.warning(f"[ProviderRegistry] Error in provider '{name}': {exc}", exc_info=True)
        return dict(fallback)


def list_registered_providers() -> list[str]:
    """列出所有已注册的 Provider 名称。"""
    return list(_REGISTRY.keys())
