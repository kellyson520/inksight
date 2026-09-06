"""Durable FIFO queue for device alert delivery."""
from __future__ import annotations

import asyncio
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any


class DeviceAlertQueue:
    def __init__(self, path: str | Path, *, per_device_limit: int = 8) -> None:
        self.path = Path(path)
        self.per_device_limit = max(1, int(per_device_limit))
        self._init_lock = asyncio.Lock()
        self._initialized = False

    async def initialize(self) -> None:
        async with self._init_lock:
            if self._initialized:
                return
            self.path.parent.mkdir(parents=True, exist_ok=True)
            await asyncio.to_thread(self._initialize_sync)
            self._initialized = True

    def _initialize_sync(self) -> None:
        with sqlite3.connect(self.path) as db:
            db.execute(
                "CREATE TABLE IF NOT EXISTS device_alerts (id INTEGER PRIMARY KEY AUTOINCREMENT, mac TEXT NOT NULL, payload TEXT NOT NULL, created_at REAL NOT NULL)"
            )
            db.execute("CREATE INDEX IF NOT EXISTS idx_device_alerts_mac_id ON device_alerts(mac, id)")
            db.commit()

    async def enqueue(self, mac: str, alert: dict[str, Any]) -> None:
        await self.initialize()
        await asyncio.to_thread(self._enqueue_sync, mac.upper(), dict(alert))

    def _enqueue_sync(self, mac: str, alert: dict[str, Any]) -> None:
        with sqlite3.connect(self.path, timeout=10.0) as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute(
                "INSERT INTO device_alerts(mac, payload, created_at) VALUES (?, ?, ?)",
                (mac, json.dumps(alert, ensure_ascii=False), datetime.now().timestamp()),
            )
            db.execute(
                "DELETE FROM device_alerts WHERE mac = ? AND id NOT IN (SELECT id FROM device_alerts WHERE mac = ? ORDER BY id DESC LIMIT ?)",
                (mac, mac, self.per_device_limit),
            )
            db.commit()

    async def pop(self, mac: str, *, now: datetime | None = None) -> dict[str, Any] | None:
        await self.initialize()
        return await asyncio.to_thread(self._pop_sync, mac.upper(), now or datetime.now())

    def _pop_sync(self, mac: str, now: datetime) -> dict[str, Any] | None:
        with sqlite3.connect(self.path, timeout=10.0) as db:
            db.row_factory = sqlite3.Row
            db.execute("BEGIN IMMEDIATE")
            rows = db.execute("SELECT id, payload FROM device_alerts WHERE mac = ? ORDER BY id", (mac,)).fetchall()
            for row in rows:
                payload = json.loads(row["payload"])
                expires_at = payload.get("expires_at")
                if expires_at:
                    try:
                        if datetime.fromisoformat(expires_at) < now:
                            db.execute("DELETE FROM device_alerts WHERE id = ?", (row["id"],))
                            continue
                    except (TypeError, ValueError):
                        pass
                db.execute("DELETE FROM device_alerts WHERE id = ?", (row["id"],))
                db.commit()
                return payload
            db.commit()
            return None
