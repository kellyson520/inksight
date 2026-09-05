"""Unified outbound HTTP policy for public data sources."""
from __future__ import annotations

import ipaddress
import math
import random
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping
from urllib.parse import urlparse

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
    def _validate_url(url: str, policy: RequestPolicy) -> None:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError(f"unsupported URL: {url}")
        host = parsed.hostname.lower().rstrip(".")
        if policy.allowed_hosts and host not in policy.allowed_hosts:
            raise ValueError(f"host not allowed: {host}")
        if host in {"localhost", "metadata.google.internal"}:
            raise ValueError(f"private URL blocked: {url}")
        try:
            address = ipaddress.ip_address(host)
        except ValueError:
            return
        if address.is_private or address.is_loopback or address.is_link_local or address.is_reserved:
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

    def _get(self, url: str, headers: dict[str, str], policy: RequestPolicy) -> httpx.Response:
        client = self.client_factory(
            timeout=policy.timeout,
            follow_redirects=policy.follow_redirects,
            verify=policy.verify,
        )
        if hasattr(client, "__enter__"):
            with client as managed:
                return managed.get(url, headers=headers, follow_redirects=policy.follow_redirects)
        return client.get(url, headers=headers, follow_redirects=policy.follow_redirects)

    def get_bytes(
        self,
        url: str,
        *,
        headers: Mapping[str, str] | None = None,
        policy: RequestPolicy | None = None,
    ) -> HttpResponse:
        effective = policy or self.policy
        self._validate_url(url, effective)
        max_attempts = min(5, max(1, int(effective.max_attempts)))
        max_bytes = max(1, min(32 * 1024 * 1024, int(effective.max_response_bytes)))
        request_headers = {
            "User-Agent": "InkSightOutboundHttp/1.0",
            "Referer": self._header_referer(url, headers),
        }
        request_headers.update({str(k): str(v) for k, v in (headers or {}).items()})
        started = time.perf_counter()
        last_error: Exception | None = None

        for attempt in range(1, max_attempts + 1):
            try:
                response = self._get(url, request_headers, effective)
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
                return HttpResponse(response.status_code, dict(response.headers), content, url, attempt, elapsed)
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

    def get_text(self, url: str, *, headers: Mapping[str, str] | None = None, policy: RequestPolicy | None = None) -> HttpResponse:
        return self.get_bytes(url, headers=headers, policy=policy)

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

    def get_json(self, url: str, *, headers: Mapping[str, str] | None = None, policy: RequestPolicy | None = None) -> HttpResponse:
        response = self.get_bytes(url, headers=headers, policy=policy)
        response.json()
        return response


outbound_http = OutboundHttp()
