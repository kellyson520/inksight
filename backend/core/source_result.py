"""Common result contract for external content sources."""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from typing import Any, Generic, TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class SourceResult(Generic[T]):
    data: T
    source: str
    source_status: str = "fresh"
    fetched_at: datetime | None = None
    expires_at: datetime | None = None
    error: str | None = None

    @classmethod
    def fresh(cls, data: T, *, source: str, ttl_seconds: int | None = None) -> "SourceResult[T]":
        now = datetime.now(timezone.utc)
        expires = now.timestamp() + ttl_seconds if ttl_seconds is not None else None
        return cls(data=data, source=source, fetched_at=now, expires_at=datetime.fromtimestamp(expires, timezone.utc) if expires else None)

    @classmethod
    def fallback(cls, data: T, *, source: str, reason: str) -> "SourceResult[T]":
        return cls(data=data, source=source, source_status="fallback", error=reason)

    def as_stale(self, *, reason: str) -> "SourceResult[T]":
        return replace(self, source_status="stale", error=reason)

    @property
    def is_available(self) -> bool:
        return self.source_status in {"fresh", "stale", "fallback"}
