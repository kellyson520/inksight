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

    def snapshot(self) -> dict[str, Any]:
        return {"events": list(self._events), "dependency_metrics": self.dependency_metrics()}


obs = Observability()
