"""Unified outbound HTTP policy for public data sources."""
from __future__ import annotations

import ipaddress
import math
import random
import socket
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping
from urllib.parse import urljoin, urlparse

import httpx

from .observability import obs


@dataclass(frozen=True)
class RequestPolicy:
    timeout: httpx.Timeout = field(default_factory=lambda: httpx.Timeout(connect=6.0, read=10.0, write=6.0, pool=6.0))
    max_attempts: int = 3
    backoff_base: float = 0.25
    max_response_bytes: int = 8 * 1024 * 1024
    verify: bool = True
    follow_redirects: bool = False
    allowed_hosts: frozenset[str] | None = None


@dataclass(frozen=True)
class HttpResponse:
    status_code: int
    headers: Mapping[str, str]
    content: bytes
    url: str
    attempts: int
    elapsed_ms: float

    @property
    def text(self) -> str:
        return self.content.decode("utf-8", errors="replace")

    def json(self) -> Any:
        import json
        return json.loads(self.content)


class RetryableHttpError(ValueError):
    pass


class OutboundHttp:
    RETRYABLE_STATUS_CODES = frozenset({408, 425, 429})

    def __init__(
        self,
        *,
        client_factory: Callable[..., httpx.Client] | None = None,
        policy: RequestPolicy | None = None,
    ) -> None:
        self.client_factory = client_factory or httpx.Client
        self.policy = policy or RequestPolicy()

    @staticmethod
    def _validate_url(url: str, policy: RequestPolicy, proxy_url: str | None = None) -> None:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError(f"unsupported URL: {url}")
        host = parsed.hostname.lower().rstrip(".")
        if policy.allowed_hosts and host not in policy.allowed_hosts:
            raise ValueError(f"host not allowed: {host}")
        if host in {"localhost", "metadata.google.internal"} or host.endswith(".local"):
            raise ValueError(f"private URL blocked: {url}")
        try:
            address = ipaddress.ip_address(host)
            addresses = [address]
        except ValueError:
            if proxy_url:
                return
            try:
                infos = socket.getaddrinfo(host, parsed.port or (443 if parsed.scheme == "https" else 80), type=socket.SOCK_STREAM)
            except socket.gaierror as exc:
                raise ValueError(f"host resolution failed: {host}") from exc
            addresses = [ipaddress.ip_address(info[4][0]) for info in infos]

        def _is_private_or_blocked(addr: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
            if addr.is_loopback or addr.is_link_local or addr.is_unspecified or addr.is_reserved:
                return True
            if isinstance(addr, ipaddress.IPv6Address):
                # 检查 IPv4-mapped IPv6 地址 (如 ::ffff:127.0.0.1, ::ffff:169.254.169.254)
                if addr.ipv4_mapped:
                    return _is_private_or_blocked(addr.ipv4_mapped)
                return (
                    addr.is_private
                    or (addr in ipaddress.IPv6Network("fc00::/7"))
                    or (addr in ipaddress.IPv6Network("fe80::/10"))
                )
            # IPv4 检查：RFC 1918 私网、保留地址以及 RFC 6598 运营商级 NAT (100.64.0.0/10)
            cgnat = ipaddress.IPv4Network("100.64.0.0/10")
            return addr.is_private or addr.is_reserved or (addr in cgnat)

        # 只要解析出的任一 IP 属于私有/保留/环回/拦截范围，立即防御性拦截
        if addresses and any(_is_private_or_blocked(a) for a in addresses):
            raise ValueError(f"private URL blocked: {url}")

    @staticmethod
    def _retryable_status(status: int) -> bool:
        return status in OutboundHttp.RETRYABLE_STATUS_CODES or 500 <= status <= 599

    @staticmethod
    def _header_referer(url: str, headers: Mapping[str, str] | None) -> str:
        if headers and headers.get("Referer"):
            return str(headers["Referer"])
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}/"

    def _get(self, url: str, headers: dict[str, str], policy: RequestPolicy, proxy_url: str | None = None) -> httpx.Response:
        client_kwargs: dict[str, Any] = {
            "timeout": policy.timeout,
            "follow_redirects": False,
            "verify": policy.verify,
        }
        if proxy_url:
            # Check if client_factory accepts 'proxy' or 'proxies' (httpx <= 0.25 uses proxies, >= 0.26 uses proxy)
            try:
                import inspect
                sig = inspect.signature(self.client_factory)
                if "proxy" in sig.parameters:
                    client_kwargs["proxy"] = proxy_url
                else:
                    client_kwargs["proxies"] = proxy_url
            except Exception:
                client_kwargs["proxies"] = proxy_url
        try:
            client = self.client_factory(**client_kwargs)
        except TypeError as e:
            if "proxies" in str(e) and proxy_url:
                client_kwargs.pop("proxies", None)
                client_kwargs["proxy"] = proxy_url
                client = self.client_factory(**client_kwargs)
            elif "proxy" in str(e) and proxy_url:
                client_kwargs.pop("proxy", None)
                client_kwargs["proxies"] = proxy_url
                client = self.client_factory(**client_kwargs)
            else:
                raise
        if hasattr(client, "__enter__"):
            with client as managed:
                return managed.get(url, headers=headers, follow_redirects=False)
        return client.get(url, headers=headers, follow_redirects=False)

    def get_bytes(
        self,
        url: str,
        *,
        headers: Mapping[str, str] | None = None,
        policy: RequestPolicy | None = None,
        proxy_url: str | None = None,
    ) -> HttpResponse:
        effective = policy or self.policy
        self._validate_url(url, effective, proxy_url=proxy_url)
        max_attempts = min(5, max(1, int(effective.max_attempts)))
        max_bytes = max(1, min(32 * 1024 * 1024, int(effective.max_response_bytes)))
        request_headers = {
            "User-Agent": "InkSightOutboundHttp/1.0",
            "Referer": self._header_referer(url, headers),
        }
        request_headers.update({str(k): str(v) for k, v in (headers or {}).items()})
        started = time.perf_counter()
        last_error: Exception | None = None

        current_url = url
        for attempt in range(1, max_attempts + 1):
            try:
                response = self._get(current_url, request_headers, effective, proxy_url=proxy_url)
                if 300 <= response.status_code < 400 and effective.follow_redirects:
                    location = response.headers.get("location")
                    if not location:
                        raise ValueError(f"redirect missing location: HTTP {response.status_code}")
                    current_url = urljoin(current_url, location)
                    self._validate_url(current_url, effective, proxy_url=proxy_url)
                    continue
                if response.status_code >= 300:
                    if self._retryable_status(response.status_code) and attempt < max_attempts:
                        if effective.backoff_base > 0:
                            time.sleep(effective.backoff_base * (2 ** (attempt - 1)) + random.random() * 0.05)
                        continue
                    error_type = RetryableHttpError if self._retryable_status(response.status_code) else ValueError
                    raise error_type(f"HTTP {response.status_code}")
                content = response.content
                if len(content) > max_bytes:
                    raise ValueError(f"response too large: {len(content)} bytes")
                elapsed = round((time.perf_counter() - started) * 1000, 2)
                obs.emit("dependency.completed", {
                    "operation": "http.get",
                    "url_host": urlparse(url).hostname,
                    "status": response.status_code,
                    "attempts": attempt,
                    "duration_ms": elapsed,
                })
                return HttpResponse(response.status_code, dict(response.headers), content, current_url, attempt, elapsed)
            except (httpx.TimeoutException, httpx.NetworkError, httpx.RemoteProtocolError, ValueError) as exc:
                last_error = exc
                if isinstance(exc, ValueError) and not isinstance(exc, RetryableHttpError):
                    break
                if attempt < max_attempts and effective.backoff_base > 0:
                    time.sleep(effective.backoff_base * (2 ** (attempt - 1)) + random.random() * 0.05)

        elapsed = round((time.perf_counter() - started) * 1000, 2)
        obs.emit("dependency.failed", {
            "operation": "http.get",
            "url_host": urlparse(url).hostname,
            "attempts": max_attempts,
            "retry_count": max(0, max_attempts - 1),
            "duration_ms": elapsed,
            "error_type": type(last_error).__name__ if last_error else "UnknownError",
        })
        raise last_error or ValueError("outbound request failed")

    def get_stream_bytes(
        self,
        url: str,
        *,
        headers: Mapping[str, str] | None = None,
        policy: RequestPolicy | None = None,
        proxy_url: str | None = None,
    ) -> HttpResponse:
        effective = policy or self.policy
        self._validate_url(url, effective, proxy_url=proxy_url)
        max_bytes = max(1, min(32 * 1024 * 1024, int(effective.max_response_bytes)))
        request_headers = {"User-Agent": "InkSightOutboundHttp/1.0", "Referer": self._header_referer(url, headers)}
        request_headers.update({str(k): str(v) for k, v in (headers or {}).items()})
        client_kwargs = {"timeout": effective.timeout, "follow_redirects": False, "verify": effective.verify}
        if proxy_url:
            # Check if client_factory accepts 'proxy' or 'proxies' (httpx <= 0.25 uses proxies, >= 0.26 uses proxy)
            try:
                import inspect
                sig = inspect.signature(self.client_factory)
                if "proxy" in sig.parameters:
                    client_kwargs["proxy"] = proxy_url
                else:
                    client_kwargs["proxies"] = proxy_url
            except Exception:
                client_kwargs["proxies"] = proxy_url
        try:
            client = self.client_factory(**client_kwargs)
        except TypeError as e:
            if "proxies" in str(e) and proxy_url:
                client_kwargs.pop("proxies", None)
                client_kwargs["proxy"] = proxy_url
                client = self.client_factory(**client_kwargs)
            elif "proxy" in str(e) and proxy_url:
                client_kwargs.pop("proxy", None)
                client_kwargs["proxies"] = proxy_url
                client = self.client_factory(**client_kwargs)
            else:
                raise
        started = time.perf_counter()
        chunks: list[bytes] = []
        total = 0
        try:
            with client.stream("GET", url, headers=request_headers, follow_redirects=False) as response:
                if response.status_code >= 300:
                    raise ValueError(f"HTTP {response.status_code}")
                for chunk in response.iter_bytes():
                    total += len(chunk)
                    if total > max_bytes:
                        raise ValueError(f"response too large: {total} bytes")
                    chunks.append(chunk)
            elapsed = round((time.perf_counter() - started) * 1000, 2)
            return HttpResponse(response.status_code, dict(response.headers), b"".join(chunks), url, 1, elapsed)
        finally:
            close = getattr(client, "close", None)
            if close and not hasattr(client, "__enter__"):
                close()

    def get_text(self, url: str, *, headers: Mapping[str, str] | None = None, policy: RequestPolicy | None = None, proxy_url: str | None = None) -> HttpResponse:
        return self.get_bytes(url, headers=headers, policy=policy, proxy_url=proxy_url)

    def head(self, url: str, *, headers: Mapping[str, str] | None = None, policy: RequestPolicy | None = None) -> HttpResponse:
        effective = policy or self.policy
        self._validate_url(url, effective)
        request_headers = {"User-Agent": "InkSightOutboundHttp/1.0"}
        request_headers.update({str(k): str(v) for k, v in (headers or {}).items()})
        client = self.client_factory(
            timeout=effective.timeout,
            follow_redirects=effective.follow_redirects,
            verify=effective.verify,
        )
        started = time.perf_counter()
        try:
            if hasattr(client, "__enter__"):
                with client as managed:
                    response = managed.head(url, headers=request_headers, follow_redirects=effective.follow_redirects)
            else:
                response = client.head(url, headers=request_headers, follow_redirects=effective.follow_redirects)
        finally:
            if not hasattr(client, "__enter__"):
                close = getattr(client, "close", None)
                if close:
                    close()
        elapsed = round((time.perf_counter() - started) * 1000, 2)
        event = {
            "operation": "http.head",
            "url_host": urlparse(url).hostname,
            "status": response.status_code,
            "attempts": 1,
            "duration_ms": elapsed,
        }
        if response.status_code >= 300:
            obs.emit("dependency.failed", {**event, "error_type": "HTTPStatusError"})
        else:
            obs.emit("dependency.completed", event)
        return HttpResponse(response.status_code, dict(response.headers), response.content, str(response.url), 1, elapsed)

    def post_json(self, url: str, *, json_body: Any, headers: Mapping[str, str] | None = None, policy: RequestPolicy | None = None) -> HttpResponse:
        effective = policy or self.policy
        self._validate_url(url, effective)
        request_headers = {"User-Agent": "InkSightOutboundHttp/1.0", "Content-Type": "application/json"}
        request_headers.update({str(k): str(v) for k, v in (headers or {}).items()})
        client = self.client_factory(timeout=effective.timeout, follow_redirects=effective.follow_redirects, verify=effective.verify)
        started = time.perf_counter()
        if hasattr(client, "__enter__"):
            with client as managed:
                response = managed.post(url, json=json_body, headers=request_headers, follow_redirects=effective.follow_redirects)
        else:
            response = client.post(url, json=json_body, headers=request_headers, follow_redirects=effective.follow_redirects)
        if response.status_code >= 300:
            raise ValueError(f"HTTP {response.status_code}")
        if len(response.content) > effective.max_response_bytes:
            raise ValueError(f"response too large: {len(response.content)} bytes")
        elapsed = round((time.perf_counter() - started) * 1000, 2)
        obs.emit("dependency.completed", {"operation": "http.post_json", "url_host": urlparse(url).hostname, "status": response.status_code, "attempts": 1, "retry_count": 0, "duration_ms": elapsed})
        return HttpResponse(response.status_code, dict(response.headers), response.content, url, 1, elapsed)

    def get_json(self, url: str, *, headers: Mapping[str, str] | None = None, policy: RequestPolicy | None = None, proxy_url: str | None = None) -> HttpResponse:
        response = self.get_bytes(url, headers=headers, policy=policy, proxy_url=proxy_url)
        response.json()
        return response


outbound_http = OutboundHttp()
