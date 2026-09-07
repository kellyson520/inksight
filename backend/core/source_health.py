from __future__ import annotations

import time
from dataclasses import dataclass
from enum import Enum
from typing import Any


class SourceState(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    COOLDOWN = "cooldown"
    HALF_OPEN = "half_open"


@dataclass
class SourceRecord:
    source: str
    state: SourceState = SourceState.HEALTHY
    consecutive_failures: int = 0
    consecutive_successes: int = 0
    total_calls: int = 0
    total_failures: int = 0
    last_error: str | None = None
    last_success_time: float | None = None
    last_failure_time: float | None = None


class SourceHealthRegistry:
    """Tracks upstream data source health, consecutive failures, and cooldown circuit breaking."""

    def __init__(self, *, failure_threshold: int = 3, cooldown_seconds: float = 60.0) -> None:
        self.failure_threshold = max(1, failure_threshold)
        self.cooldown_seconds = max(0.1, cooldown_seconds)
        self._sources: dict[str, SourceRecord] = {}

    def _get_or_create(self, source: str) -> SourceRecord:
        if source not in self._sources:
            self._sources[source] = SourceRecord(source=source)
        return self._sources[source]

    def should_allow_request(self, source: str) -> bool:
        record = self._get_or_create(source)
        if record.state in (SourceState.HEALTHY, SourceState.DEGRADED):
            return True

        if record.state == SourceState.COOLDOWN:
            now = time.time()
            last_fail = record.last_failure_time or 0.0
            if now - last_fail >= self.cooldown_seconds:
                record.state = SourceState.HALF_OPEN
                return True
            return False

        if record.state == SourceState.HALF_OPEN:
            return True

        return True

    def record_success(self, source: str) -> None:
        record = self._get_or_create(source)
        record.total_calls += 1
        record.consecutive_successes += 1
        record.consecutive_failures = 0
        record.last_success_time = time.time()
        record.state = SourceState.HEALTHY

    def record_failure(self, source: str, reason: str = "") -> None:
        now = time.time()
        record = self._get_or_create(source)
        record.total_calls += 1
        record.total_failures += 1
        record.consecutive_failures += 1
        record.consecutive_successes = 0
        record.last_failure_time = now
        record.last_error = reason

        if record.consecutive_failures >= self.failure_threshold:
            record.state = SourceState.COOLDOWN
        else:
            record.state = SourceState.DEGRADED

    def get_status(self, source: str) -> dict[str, Any]:
        record = self._get_or_create(source)
        # Check if cooldown has naturally expired into half-open probe availability
        state = record.state
        if state == SourceState.COOLDOWN:
            now = time.time()
            if now - (record.last_failure_time or 0.0) >= self.cooldown_seconds:
                state = SourceState.HALF_OPEN

        return {
            "source": record.source,
            "state": state,
            "consecutive_failures": record.consecutive_failures,
            "consecutive_successes": record.consecutive_successes,
            "total_calls": record.total_calls,
            "total_failures": record.total_failures,
            "last_error": record.last_error,
            "last_success_time": record.last_success_time,
            "last_failure_time": record.last_failure_time,
        }

    def summary(self) -> dict[str, Any]:
        healthy_count = 0
        degraded_count = 0
        cooldown_count = 0
        sources_status: dict[str, Any] = {}

        for name in sorted(self._sources.keys()):
            st = self.get_status(name)
            sources_status[name] = st
            state = st["state"]
            if state == SourceState.HEALTHY:
                healthy_count += 1
            elif state == SourceState.COOLDOWN:
                cooldown_count += 1
            else:
                degraded_count += 1

        return {
            "total_sources": len(self._sources),
            "healthy_count": healthy_count,
            "degraded_count": degraded_count,
            "cooldown_count": cooldown_count,
            "sources": sources_status,
        }


# Global singleton instance
source_health = SourceHealthRegistry()
