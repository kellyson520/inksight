"""Snapshot diff runner for hotlist sources."""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import tempfile
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from .event_outbox import EventOutbox

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
        outbox: EventOutbox | None = None,
        snapshot_path: str | Path | None = None,
    ) -> None:
        self.service = service
        self.outbox = outbox
        self.publish = publish or (lambda _event: None)
        self.snapshot_path = Path(snapshot_path) if snapshot_path else None
        self._snapshots = self._load_snapshots()

    def _load_snapshots(self) -> dict[str, dict[str, int]]:
        if not self.snapshot_path:
            return {}
        try:
            data = json.loads(self.snapshot_path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except (OSError, ValueError, TypeError):
            return {}

    def _save_snapshots(self) -> None:
        if not self.snapshot_path:
            return
        self.snapshot_path.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_name = tempfile.mkstemp(prefix=".hotlist-snapshot-", dir=self.snapshot_path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(self._snapshots, handle, ensure_ascii=False, indent=2)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_name, self.snapshot_path)
        finally:
            if os.path.exists(temp_name):
                os.unlink(temp_name)

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
        if source_status != "fresh":
            return []
        events = self.diff(platform, result.get("items", []))
        self._save_snapshots()
        for event in events:
            event["source_status"] = source_status
            event["is_realtime"] = source_status == "fresh"
            event["target_mac"] = "*"
            event["event_id"] = f"hotlist:{platform}:{event['item_id']}:{event['kind']}:{event.get('old_rank', '')}:{event.get('rank', '')}"
            if self.outbox is not None:
                self.outbox.publish(event)
                published = True
            else:
                published = self.publish(event)
            if isinstance(published, Awaitable):
                await published
        return events
