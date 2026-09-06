"""Durable outbox consumer with bounded retry and expiry."""
from __future__ import annotations

import asyncio
import os
import time
import uuid
from collections.abc import Awaitable, Callable
from typing import Any

from .event_outbox import EventOutbox
from .observability import obs


class EventDispatcher:
    def __init__(
        self,
        outbox: EventOutbox,
        *,
        publish: Callable[[dict[str, Any]], Any],
        max_attempts: int = 3,
        backoff: float = 0.5,
        max_age_seconds: float = 24 * 3600,
        worker_id: str | None = None,
        lease_seconds: float = 60.0,
    ) -> None:
        self.outbox = outbox
        self.publish = publish
        self.max_attempts = max(1, min(5, max_attempts))
        self.backoff = max(0.0, backoff)
        self.max_age_seconds = max(1.0, max_age_seconds)
        self.worker_id = worker_id or f"dispatcher-{os.getpid()}-{uuid.uuid4().hex[:8]}"
        self.lease_seconds = max(1.0, float(lease_seconds))

    async def dispatch_once(self, limit: int = 100) -> dict[str, int]:
        stats = {"published": 0, "failed": 0, "expired": 0}
        now = time.time()
        for event in self.outbox.claim_pending(self.worker_id, lease_seconds=self.lease_seconds, limit=limit):
            event_id = str(event.get("event_id", ""))
            if now - float(event.get("created_at", now)) > self.max_age_seconds:
                self.outbox.ack(event_id, worker_id=self.worker_id)
                obs.emit("event.expired", {"event_id": event_id, "kind": event.get("kind", "")})
                stats["expired"] += 1
                continue
            success = False
            for attempt in range(1, self.max_attempts + 1):
                event["attempts"] = attempt
                try:
                    result = self.publish(event)
                    if isinstance(result, Awaitable):
                        result = await result
                    success = result is True
                    if success:
                        break
                except Exception:
                    success = False
                if attempt < self.max_attempts and self.backoff:
                    await asyncio.sleep(self.backoff * attempt)
            if not success:
                self.outbox.update(event, worker_id=self.worker_id)
            if success:
                self.outbox.ack(event_id, worker_id=self.worker_id)
                obs.emit("event.published", {"event_id": event_id, "kind": event.get("kind", ""), "attempts": event.get("attempts", 1)})
                stats["published"] += 1
            else:
                obs.emit("event.failed", {"event_id": event_id, "kind": event.get("kind", ""), "attempts": self.max_attempts})
                stats["failed"] += 1
        return stats
