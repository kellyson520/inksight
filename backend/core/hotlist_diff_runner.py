"""Snapshot diff runner for hotlist sources."""
from __future__ import annotations

import asyncio
import logging
import re
from collections.abc import Awaitable, Callable
from typing import Any

logger = logging.getLogger(__name__)


def _item_id(item: dict[str, Any]) -> str:
    explicit = item.get("id") or item.get("item_id")
    value = str(explicit or item.get("title") or "").strip().lower()
    return re.sub(r"[^\w\u4e00-\u9fff]+", "-", value).strip("-")


class HotlistDiffRunner:
    def __init__(
        self,
        service: Any | None = None,
        *,
        publish: Callable[[dict[str, Any]], Any] | None = None,
    ) -> None:
        self.service = service
        self.publish = publish or (lambda _event: None)
        self._snapshots: dict[str, dict[str, int]] = {}

    def diff(self, platform: str, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        current = {_item_id(item): index + 1 for index, item in enumerate(items) if _item_id(item)}
        previous = self._snapshots.get(platform)
        if previous is None:
            self._snapshots[platform] = current
            return []
        events: list[dict[str, Any]] = []
        for item_id, rank in current.items():
            if item_id not in previous:
                events.append({"kind": "new", "platform": platform, "item_id": item_id, "rank": rank})
            elif previous[item_id] != rank:
                events.append({"kind": "rank_changed", "platform": platform, "item_id": item_id, "old_rank": previous[item_id], "rank": rank})
        for item_id, rank in previous.items():
            if item_id not in current:
                events.append({"kind": "removed", "platform": platform, "item_id": item_id, "old_rank": rank})
        self._snapshots[platform] = current
        return events

    async def run_once(self, platform: str, limit: int = 20) -> list[dict[str, Any]]:
        if self.service is None:
            return []
        result = await self.service.get_hotlist(platform, limit=limit)
        source_status = result.get("source_status", "fresh")
        events = self.diff(platform, result.get("items", []))
        for event in events:
            event["source_status"] = source_status
            event["is_realtime"] = source_status == "fresh"
            published = self.publish(event)
            if isinstance(published, Awaitable):
                await published
        return events
