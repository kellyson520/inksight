"""Adapters from canonical outbox events to notification channels."""
from __future__ import annotations

from typing import Any


class DeviceEventDeliveryAdapter:
    def __init__(self, push_dispatcher: Any) -> None:
        self.push_dispatcher = push_dispatcher

    async def publish(self, event: dict[str, Any]) -> bool:
        if event.get("is_realtime") is False:
            return True
        if not event.get("target_mac") or event.get("target_mac") == "*":
            return False
        title = f"热榜更新 · {event.get('platform', 'unknown')}"
        item_id = event.get("item_id", "")
        kind = event.get("kind", "changed")
        rank = event.get("rank") or event.get("old_rank") or ""
        message = f"{kind}: {item_id} {rank}".strip()
        return bool(
            await self.push_dispatcher.push_to_device(
                mac=str(event["target_mac"]),
                sender="HOTLIST",
                message=f"{title}: {message}",
                level="info" if kind == "new" else "warning",
            )
        )
