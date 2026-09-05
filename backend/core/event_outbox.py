"""Small durable, idempotent JSON event outbox."""
from __future__ import annotations

import json
import os
import tempfile
import time
from pathlib import Path
from typing import Any


class EventOutbox:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._events: list[dict[str, Any]] = []
        self._load()

    def _load(self) -> None:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(data, list):
                self._events = [item for item in data if isinstance(item, dict)]
        except (OSError, ValueError, TypeError):
            self._events = []
            if self.path.exists():
                quarantine = self.path.with_name(f"{self.path.name}.corrupt-{int(time.time() * 1000)}")
                try:
                    os.replace(self.path, quarantine)
                except OSError:
                    pass

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_name = tempfile.mkstemp(prefix=".events-", dir=self.path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(self._events, handle, ensure_ascii=False, indent=2)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_name, self.path)
        finally:
            if os.path.exists(temp_name):
                os.unlink(temp_name)

    def publish(self, event: dict[str, Any]) -> bool:
        event_id = str(event.get("event_id") or "").strip()
        if not event_id:
            raise ValueError("event_id is required")
        if any(str(item.get("event_id")) == event_id for item in self._events):
            return False
        item = dict(event)
        item.setdefault("created_at", time.time())
        item.setdefault("attempts", 0)
        self._events.append(item)
        self._save()
        return True

    def list_pending(self, limit: int | None = None) -> list[dict[str, Any]]:
        events = list(self._events)
        return events if limit is None else events[: max(0, limit)]

    def update(self, event: dict[str, Any]) -> None:
        event_id = str(event.get("event_id") or "")
        for index, item in enumerate(self._events):
            if str(item.get("event_id")) == event_id:
                self._events[index] = dict(event)
                self._save()
                return
        raise KeyError(event_id)

    def ack(self, event_id: str) -> bool:
        before = len(self._events)
        self._events = [item for item in self._events if str(item.get("event_id")) != event_id]
        if len(self._events) == before:
            return False
        self._save()
        return True
