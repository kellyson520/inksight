"""Shared resilient remote-media fetching infrastructure.

All upstream callers should use :data:`media_fetcher` instead of creating their
own HTTP clients. The service handles bounded retries, URL candidates, domain
referers, and a small persistent cache.
"""
from __future__ import annotations

import hashlib
import os
import math
import random
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence
from urllib.parse import urlparse

import ipaddress

import httpx


def _backend_root() -> Path:
    return Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class MediaFetchResult:
    data: bytes
    url: str
    cache_hit: bool


class MediaFetchError(RuntimeError):
    """Raised after all URL candidates and retry attempts are exhausted."""

    def __init__(self, message: str, *, attempts: list[str] | None = None) -> None:
        super().__init__(message)
        self.attempts = attempts or []


class MediaFetcher:
    """Bounded, cache-backed fetcher for remote images and other media."""

    RETRYABLE_STATUS_CODES = frozenset({408, 425, 429})

    def __init__(
        self,
        *,
        cache_dir: str | Path | None = None,
        client_factory: Callable[..., httpx.Client] | None = None,
        max_attempts: int | None = None,
        backoff_base: float | None = None,
        failure_cooldown: float | None = None,
        timeout: httpx.Timeout | None = None,
        max_response_bytes: int | None = None,
    ) -> None:
        configured_cache = os.getenv("INKSIGHT_MEDIA_CACHE_DIR", "")
        self.cache_dir = Path(cache_dir) if cache_dir is not None else (_backend_root() / configured_cache if configured_cache else _backend_root() / "data" / "image_cache")
        self.max_attempts = min(5, max(1, max_attempts if max_attempts is not None else self._env_int("INKSIGHT_MEDIA_MAX_ATTEMPTS", 3)))
        self.backoff_base = self._positive_float(backoff_base, "INKSIGHT_MEDIA_BACKOFF_BASE", 0.25, allow_zero=True)
        self.failure_cooldown = self._positive_float(failure_cooldown, "INKSIGHT_MEDIA_FAILURE_COOLDOWN", 30.0, allow_zero=True)
        configured_max_bytes = max_response_bytes if max_response_bytes is not None else self._env_int("INKSIGHT_MEDIA_MAX_RESPONSE_BYTES", 8 * 1024 * 1024)
        self.max_response_bytes = min(32 * 1024 * 1024, max(1024, configured_max_bytes))
        self.timeout = timeout or httpx.Timeout(
            connect=self._positive_float(None, "INKSIGHT_MEDIA_TIMEOUT_CONNECT", 6.0),
            read=self._positive_float(None, "INKSIGHT_MEDIA_TIMEOUT_READ", 10.0),
            write=self._positive_float(None, "INKSIGHT_MEDIA_TIMEOUT_WRITE", 6.0),
            pool=self._positive_float(None, "INKSIGHT_MEDIA_TIMEOUT_POOL", 6.0),
        )
        self.client_factory = client_factory or httpx.Client
        self._memory_cache: dict[str, bytes] = {}
        self._failed_until: dict[str, float] = {}

    @staticmethod
    def _env_int(name: str, default: int) -> int:
        try:
            return int(os.getenv(name, str(default)))
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _env_float(name: str, default: float) -> float:
        try:
            return float(os.getenv(name, str(default)))
        except (TypeError, ValueError):
            return default

    @classmethod
    def _positive_float(cls, value: float | None, env_name: str, default: float, *, allow_zero: bool = False) -> float:
        candidate = value if value is not None else cls._env_float(env_name, default)
        if not math.isfinite(candidate) or candidate < 0 or (candidate == 0 and not allow_zero):
            return default
        return candidate

    @staticmethod
    def _validate_url(url: str) -> None:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise MediaFetchError(f"Unsupported media URL: {url}")
        host = parsed.hostname.lower().rstrip(".")
        if host in {"localhost", "metadata.google.internal"}:
            raise MediaFetchError(f"Blocked private media URL: {url}")
        try:
            address = ipaddress.ip_address(host)
        except ValueError:
            return
        if address.is_private or address.is_loopback or address.is_link_local or address.is_reserved:
            raise MediaFetchError(f"Blocked private media URL: {url}")

    @staticmethod
    def _normalize_urls(urls: str | Sequence[str]) -> list[str]:
        if isinstance(urls, str):
            candidates = [urls]
        else:
            candidates = list(urls)
        result: list[str] = []
        for url in candidates:
            value = str(url or "").strip()
            if value and value not in result:
                MediaFetcher._validate_url(value)
                result.append(value)
        if not result:
            raise MediaFetchError("No media URL candidates provided")
        return result

    @staticmethod
    def _default_referer(url: str) -> str:
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return ""
        return f"{parsed.scheme}://{parsed.netloc}/"

    @staticmethod
    def _cache_key(url: str) -> str:
        return hashlib.sha256(url.encode("utf-8")).hexdigest()

    def _cache_path(self, url: str) -> Path:
        return self.cache_dir / f"{self._cache_key(url)}.bin"

    def _read_cache(self, url: str) -> bytes | None:
        data = self._memory_cache.get(url)
        if data:
            return data
        path = self._cache_path(url)
        try:
            data = path.read_bytes()
        except (OSError, ValueError):
            return None
        if not data:
            try:
                path.unlink()
            except OSError:
                pass
            return None
        self._memory_cache[url] = data
        return data

    def _write_cache(self, url: str, data: bytes) -> None:
        if not data:
            return
        self._memory_cache[url] = data
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            fd, temp_name = tempfile.mkstemp(prefix=".media-", suffix=".tmp", dir=self.cache_dir)
            try:
                with os.fdopen(fd, "wb") as handle:
                    handle.write(data)
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(temp_name, self._cache_path(url))
            finally:
                try:
                    os.unlink(temp_name)
                except FileNotFoundError:
                    pass
        except OSError:
            # Cache persistence is best effort; successful network responses remain valid.
            return

    def _sleep_before_retry(self, attempt: int) -> None:
        if self.backoff_base <= 0:
            return
        delay = self.backoff_base * (2 ** (attempt - 1))
        delay += random.uniform(0, self.backoff_base * 0.2)
        time.sleep(delay)

    def _get(self, url: str, headers: dict[str, str]) -> httpx.Response:
        """Call an injected client, supporting both managed and plain clients."""
        client = self.client_factory(timeout=self.timeout, follow_redirects=False)
        if hasattr(client, "__enter__"):
            with client as managed_client:
                return managed_client.get(url, headers=headers, follow_redirects=False)
        return client.get(url, headers=headers, follow_redirects=False)

    @classmethod
    def _retryable_status(cls, status: int) -> bool:
        return status in cls.RETRYABLE_STATUS_CODES or 500 <= status <= 599

    def fetch_image(self, urls: str | Sequence[str], *, referer: str | None = None) -> MediaFetchResult:
        """Fetch an image and reject successful HTML/JSON anti-hotlink pages."""
        candidates = self._normalize_urls(urls)
        image_errors: list[str] = []
        for url in candidates:
            try:
                result = self.fetch(url, referer=referer)
            except MediaFetchError as exc:
                image_errors.extend(exc.attempts)
                continue
            content_type = ""
            # The generic fetch result intentionally stays small; validate bytes
            # using Pillow so mislabeled CDN responses cannot enter the cache.
            try:
                from io import BytesIO
                from PIL import Image
                with Image.open(BytesIO(result.data)) as image:
                    image.verify()
            except Exception:
                self._memory_cache.pop(url, None)
                try:
                    self._cache_path(url).unlink()
                except OSError:
                    pass
                image_errors.append(f"{url}: invalid image response")
                continue
            return result
        raise MediaFetchError("All image URL candidates failed: " + "; ".join(image_errors), attempts=image_errors)

    def fetch(self, urls: str | Sequence[str], *, referer: str | None = None) -> MediaFetchResult:
        candidates = self._normalize_urls(urls)
        errors: list[str] = []

        for url in candidates:
            cached = self._read_cache(url)
            if cached:
                return MediaFetchResult(data=cached, url=url, cache_hit=True)

            now = time.monotonic()
            if self._failed_until.get(url, 0.0) > now:
                errors.append(f"{url}: cooldown")
                continue

            headers = {
                "User-Agent": "Mozilla/5.0 (compatible; InkSightMediaFetcher/1.0)",
                "Referer": referer or self._default_referer(url),
            }
            for attempt in range(1, self.max_attempts + 1):
                try:
                    response = self._get(url, headers)
                    if response.status_code >= 400:
                        status_error = f"HTTP {response.status_code}"
                        if self._retryable_status(response.status_code) and attempt < self.max_attempts:
                            errors.append(f"{url}: {status_error} attempt={attempt}")
                            self._sleep_before_retry(attempt)
                            continue
                        errors.append(f"{url}: {status_error}")
                        break
                    data = response.content
                    if not data:
                        errors.append(f"{url}: empty response")
                        break
                    if len(data) > self.max_response_bytes:
                        errors.append(f"{url}: response too large")
                        break
                    self._write_cache(url, data)
                    self._failed_until.pop(url, None)
                    return MediaFetchResult(data=data, url=url, cache_hit=False)
                except (httpx.TimeoutException, httpx.NetworkError, httpx.RemoteProtocolError) as exc:
                    errors.append(f"{url}: {type(exc).__name__} attempt={attempt}")
                    if attempt < self.max_attempts:
                        self._sleep_before_retry(attempt)
                        continue
                    break
                except (httpx.HTTPError, OSError) as exc:
                    errors.append(f"{url}: {type(exc).__name__}")
                    break
            self._failed_until[url] = time.monotonic() + self.failure_cooldown

        detail = "; ".join(errors)
        raise MediaFetchError(f"All media URL candidates failed: {detail}", attempts=errors)


media_fetcher = MediaFetcher()
