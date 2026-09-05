"""
InkSight 高性能网络客户端基础设施 (HTTP Client Infrastructure)
- 单例连接池与长连接保活 (Keep-Alive Pool)，避免高并发频繁创建销毁 socket
- 统一请求头、超时时间、自动容错重试策略与生命周期管理
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from .outbound_http import OutboundHttp, RequestPolicy

logger = logging.getLogger(__name__)

_DEFAULT_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"

_async_client: httpx.AsyncClient | None = None
_sync_client: httpx.Client | None = None
_outbound_http = OutboundHttp()


def get_async_client() -> httpx.AsyncClient:
    """获取全局共享的高性能异步 HTTP 客户端。"""
    global _async_client
    if _async_client is None or _async_client.is_closed:
        limits = httpx.Limits(max_keepalive_connections=25, max_connections=60, keepalive_expiry=30.0)
        timeout = httpx.Timeout(connect=5.0, read=8.0, write=5.0, pool=5.0)
        _async_client = httpx.AsyncClient(
            limits=limits,
            timeout=timeout,
            headers={"User-Agent": _DEFAULT_USER_AGENT},
            follow_redirects=True,
            verify=False,
        )
    return _async_client


def get_sync_client() -> httpx.Client:
    """获取全局共享的高性能同步 HTTP 客户端。"""
    global _sync_client
    if _sync_client is None or _sync_client.is_closed:
        limits = httpx.Limits(max_keepalive_connections=15, max_connections=40, keepalive_expiry=30.0)
        timeout = httpx.Timeout(connect=5.0, read=10.0, write=5.0, pool=5.0)
        _sync_client = httpx.Client(
            limits=limits,
            timeout=timeout,
            headers={"User-Agent": _DEFAULT_USER_AGENT},
            follow_redirects=True,
            verify=False,
        )
    return _sync_client


async def fetch_json_async(url: str, headers: dict[str, str] | None = None, timeout: float | None = None, retries: int = 1) -> Any:
    """异步抓取 JSON 数据并带自动轻量重试。"""
    client = get_async_client()
    last_err: Exception | None = None
    try:
        policy = RequestPolicy(
            max_attempts=max(1, retries + 1),
            timeout=httpx.Timeout(connect=5.0, read=timeout or 8.0, write=5.0, pool=5.0),
        )
        return await asyncio.to_thread(lambda: _outbound_http.get_json(url, headers=headers, policy=policy).json())
    except Exception as exc:
        logger.debug("[HttpClient] JSON request failed for %s: %s", url, type(exc).__name__)
        raise exc


async def fetch_text_async(url: str, headers: dict[str, str] | None = None, timeout: float | None = None, retries: int = 1) -> str:
    """异步抓取文本数据并带自动轻量重试。"""
    client = get_async_client()
    last_err: Exception | None = None
    try:
        policy = RequestPolicy(
            max_attempts=max(1, retries + 1),
            timeout=httpx.Timeout(connect=5.0, read=timeout or 8.0, write=5.0, pool=5.0),
        )
        return (await asyncio.to_thread(lambda: _outbound_http.get_text(url, headers=headers, policy=policy))).text
    except Exception as exc:
        logger.debug("[HttpClient] text request failed for %s: %s", url, type(exc).__name__)
        raise exc


async def close_http_clients() -> None:
    """应用关闭时清理释放全局连接池。"""
    global _async_client, _sync_client
    if _async_client and not _async_client.is_closed:
        await _async_client.aclose()
        _async_client = None
    if _sync_client and not _sync_client.is_closed:
        _sync_client.close()
        _sync_client = None
