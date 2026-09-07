"""Small, dependency-free observability facade for the InkSight core."""
from __future__ import annotations

import contextvars
import json
import logging
import time
import uuid
from collections import deque
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Iterator, Mapping

logger = logging.getLogger(__name__)
_request_id: contextvars.ContextVar[str | None] = contextvars.ContextVar("inksight_request_id", default=None)
_REDACT_KEYS = ("api_key", "authorization", "cookie", "token", "secret", "password", "prompt", "transcript")


def get_request_id() -> str | None:
    return _request_id.get()


def _redact(value: Any, key: str = "") -> Any:
    if isinstance(value, bool):
        return value
    key_lower = key.lower()
    if any(part in key_lower for part in _REDACT_KEYS):
        return "[REDACTED]"
    if isinstance(value, Mapping):
        return {str(k): _redact(v, str(k)) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_redact(v, key) for v in value[:20]]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


@dataclass
class _RequestScope:
    token: contextvars.Token[str | None]

    def __enter__(self) -> "_RequestScope":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        _request_id.reset(self.token)


class _Observation:
    def __init__(self, owner: "Observability", operation: str, attributes: dict[str, Any]) -> None:
        self.owner = owner
        self.operation = operation
        self.attributes = attributes
        self.started = 0.0

    def __enter__(self) -> "_Observation":
        self.started = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        attrs = dict(self.attributes)
        attrs["operation"] = self.operation
        attrs["duration_ms"] = round((time.perf_counter() - self.started) * 1000, 2)
        if exc is not None:
            attrs["error_type"] = type(exc).__name__
            self.owner.emit("exception", attrs)
        else:
            self.owner.emit("operation.completed", attrs)


def _percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    k = (len(s) - 1) * p
    f = int(k)
    c = min(f + 1, len(s) - 1)
    d = k - f
    return round(s[f] + d * (s[c] - s[f]), 2)


class Observability:
    def __init__(self, *, max_events: int = 1000) -> None:
        self._events: deque[dict[str, Any]] = deque(maxlen=max(1, max_events))

    def emit(self, event: str, attributes: Mapping[str, Any] | None = None) -> None:
        try:
            payload: dict[str, Any] = {"event": event, "timestamp": time.time()}
            request_id = get_request_id()
            if request_id:
                payload["request_id"] = request_id
            payload.update(_redact(dict(attributes or {})))
            self._events.append(payload)
            logger.info("[OBS] %s", json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
        except Exception:
            logger.debug("[OBS] failed to emit event", exc_info=True)

    @contextmanager
    def start_request(self, request_id: str | None = None) -> Iterator[_RequestScope]:
        value = request_id or str(uuid.uuid4())
        scope = _RequestScope(_request_id.set(value))
        try:
            yield scope
        finally:
            _request_id.reset(scope.token)

    def observe(self, operation: str, **attributes: Any) -> _Observation:
        return _Observation(self, operation, attributes)

    def dependency_metrics(self) -> dict[str, Any]:
        """Return a bounded aggregate of dependency events in the current event window."""
        total = successes = failures = 0
        duration_total = 0.0
        by_host: dict[str, dict[str, Any]] = {}
        for event in self._events:
            name = event.get("event")
            if name not in {"dependency.completed", "dependency.failed"}:
                continue
            total += 1
            failed = name == "dependency.failed"
            if failed:
                failures += 1
            else:
                successes += 1
            duration = float(event.get("duration_ms") or 0.0)
            duration_total += duration
            host = str(event.get("url_host") or "unknown")
            bucket = by_host.setdefault(host, {"count": 0, "successes": 0, "failures": 0, "duration_ms": 0.0})
            bucket["count"] += 1
            bucket["failures" if failed else "successes"] += 1
            bucket["duration_ms"] += duration
        for bucket in by_host.values():
            bucket["duration_ms"] = round(bucket["duration_ms"], 2)
            bucket["avg_duration_ms"] = round(bucket["duration_ms"] / bucket["count"], 2)
        return {
            "total": total,
            "successes": successes,
            "failures": failures,
            "avg_duration_ms": round(duration_total / total, 2) if total else 0.0,
            "by_host": by_host,
        }

    def request_metrics(self) -> dict[str, Any]:
        """Return aggregated request volume, error classifications, and latency quantiles."""
        total = successes = client_errors = server_errors = 0
        durations: list[float] = []
        by_route: dict[str, dict[str, Any]] = {}

        for event in self._events:
            if event.get("event") != "request.completed":
                continue
            total += 1
            status = int(event.get("status") or 0)
            duration = float(event.get("duration_ms") or 0.0)
            durations.append(duration)

            if status < 400:
                successes += 1
            elif 400 <= status < 500:
                client_errors += 1
            else:
                server_errors += 1

            route = str(event.get("route") or "unknown")
            bucket = by_route.setdefault(route, {"count": 0, "errors": 0, "duration_ms": 0.0})
            bucket["count"] += 1
            if status >= 400:
                bucket["errors"] += 1
            bucket["duration_ms"] += duration

        for bucket in by_route.values():
            bucket["duration_ms"] = round(bucket["duration_ms"], 2)
            bucket["avg_duration_ms"] = round(bucket["duration_ms"] / bucket["count"], 2)

        return {
            "total": total,
            "successes": successes,
            "client_errors": client_errors,
            "server_errors": server_errors,
            "error_rate": round((client_errors + server_errors) / total, 4) if total else 0.0,
            "avg_duration_ms": round(sum(durations) / total, 2) if total else 0.0,
            "p50_duration_ms": _percentile(durations, 0.50),
            "p95_duration_ms": _percentile(durations, 0.95),
            "p99_duration_ms": _percentile(durations, 0.99),
            "by_route": by_route,
        }

    def render_metrics(self) -> dict[str, Any]:
        """Return aggregated rendering performance, cache-hit ratio, and fallback events."""
        total = cache_hits = fallbacks = 0
        durations: list[float] = []
        by_mode: dict[str, dict[str, Any]] = {}

        for event in self._events:
            if event.get("event") != "render.completed":
                continue
            total += 1
            hit = bool(event.get("cache_hit"))
            fallback = bool(event.get("fallback"))
            if hit:
                cache_hits += 1
            if fallback:
                fallbacks += 1

            duration = float(event.get("duration_ms") or 0.0)
            durations.append(duration)

            mode = str(event.get("mode") or "unknown").upper()
            bucket = by_mode.setdefault(mode, {"count": 0, "cache_hits": 0, "fallbacks": 0, "duration_ms": 0.0})
            bucket["count"] += 1
            if hit:
                bucket["cache_hits"] += 1
            if fallback:
                bucket["fallbacks"] += 1
            bucket["duration_ms"] += duration

        for bucket in by_mode.values():
            bucket["duration_ms"] = round(bucket["duration_ms"], 2)
            bucket["avg_duration_ms"] = round(bucket["duration_ms"] / bucket["count"], 2)

        return {
            "total": total,
            "cache_hits": cache_hits,
            "fallbacks": fallbacks,
            "cache_hit_rate": round(cache_hits / total, 4) if total else 0.0,
            "fallback_rate": round(fallbacks / total, 4) if total else 0.0,
            "avg_duration_ms": round(sum(durations) / total, 2) if total else 0.0,
            "p50_duration_ms": _percentile(durations, 0.50),
            "p95_duration_ms": _percentile(durations, 0.95),
            "by_mode": by_mode,
        }

    def cache_metrics(self) -> dict[str, Any]:
        """Return aggregated cache hit/miss/expiry metrics."""
        counts: dict[str, int] = {
            "memory": 0,
            "persistent": 0,
            "miss": 0,
            "expired": 0,
            "disabled": 0,
            "error": 0,
        }
        total = 0
        for event in self._events:
            if event.get("event") != "cache.result":
                continue
            total += 1
            result = str(event.get("result") or "unknown").lower()
            if result in counts:
                counts[result] += 1
            else:
                counts[result] = counts.get(result, 0) + 1

        hits = counts["memory"] + counts["persistent"]
        return {
            "total": total,
            "memory_hits": counts["memory"],
            "persistent_hits": counts["persistent"],
            "misses": counts["miss"],
            "expired": counts["expired"],
            "disabled": counts["disabled"],
            "errors": counts["error"],
            "hit_rate": round(hits / total, 4) if total else 0.0,
        }

    def operational_summary(self) -> dict[str, Any]:
        """Combine requests, dependencies, rendering, cache, source health, and recent failure diagnostics."""
        from .source_health import source_health

        recent_failures = [
            e for e in self._events
            if (e.get("event") in {"device.request.failed", "dependency.failed", "exception"})
            or (e.get("event") == "request.completed" and int(e.get("status") or 0) >= 400)
        ][-20:]

        return {
            "timestamp": time.time(),
            "events_retained": len(self._events),
            "requests": self.request_metrics(),
            "dependencies": self.dependency_metrics(),
            "renders": self.render_metrics(),
            "cache": self.cache_metrics(),
            "source_health": source_health.summary(),
            "recent_failures": recent_failures,
        }

    def snapshot(self) -> dict[str, Any]:
        return {
            "events": list(self._events),
            "dependency_metrics": self.dependency_metrics(),
            "operational_summary": self.operational_summary(),
        }


obs = Observability()
