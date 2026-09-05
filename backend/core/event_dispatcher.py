"""Durable outbox consumer with bounded retry and expiry."""
from __future__ import annotations

import asyncio
import time
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
    ) -> None:
        self.outbox = outbox
        self.publish = publish
        self.max_attempts = max(1, min(5, max_attempts))
        self.backoff = max(0.0, backoff)
        self.max_age_seconds = max(1.0, max_age_seconds)

    async def dispatch_once(self, limit: int = 100) -> dict[str, int]:
        stats = {"published": 0, "failed": 0, "expired": 0}
        now = time.time()
        for event in self.outbox.list_pending(limit):
            event_id = str(event.get("event_id", ""))
            if now - float(event.get("created_at", now)) > self.max_age_seconds:
                self.outbox.ack(event_id)
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
                    success = result is not False
                    if success:
                        break
                except Exception:
                    success = False
                if attempt < self.max_attempts and self.backoff:
                    await asyncio.sleep(self.backoff * attempt)
            if not success:
                self.outbox.update(event)
            if success:
                self.outbox.ack(event_id)
                obs.emit("event.published", {"event_id": event_id, "kind": event.get("kind", ""), "attempts": event.get("attempts", 1)})
                stats["published"] += 1
            else:
                obs.emit("event.failed", {"event_id": event_id, "kind": event.get("kind", ""), "attempts": self.max_attempts})
                stats["failed"] += 1
        return stats
