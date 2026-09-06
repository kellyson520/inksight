"""Durable, cross-worker replay protection for monitor webhooks."""
from __future__ import annotations

import asyncio
import sqlite3
import time
from pathlib import Path
from typing import Callable


class MonitorNonceStore:
    def __init__(self, path: str | Path, *, now: Callable[[], float] = time.time) -> None:
        self.path = Path(path)
        self.now = now
        self._initialized = False
        self._lock = asyncio.Lock()

    async def initialize(self) -> None:
        async with self._lock:
            if self._initialized:
                return
            self.path.parent.mkdir(parents=True, exist_ok=True)
            await asyncio.to_thread(self._initialize_sync)
            self._initialized = True

    def _initialize_sync(self) -> None:
        with sqlite3.connect(self.path) as db:
            db.execute(
                "CREATE TABLE IF NOT EXISTS monitor_webhook_nonces (nonce TEXT PRIMARY KEY, expires_at REAL NOT NULL)"
            )
            db.commit()

    async def consume(self, nonce: str, *, expires_at: float) -> bool:
        nonce = str(nonce or "").strip()
        if not nonce:
            return False
        await self.initialize()
        return await asyncio.to_thread(self._consume_sync, nonce, float(expires_at))

    def _consume_sync(self, nonce: str, expires_at: float) -> bool:
        now = float(self.now())
        with sqlite3.connect(self.path, timeout=10.0) as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute("DELETE FROM monitor_webhook_nonces WHERE expires_at <= ?", (now,))
            try:
                db.execute(
                    "INSERT INTO monitor_webhook_nonces(nonce, expires_at) VALUES (?, ?)",
                    (nonce, expires_at),
                )
            except sqlite3.IntegrityError:
                db.rollback()
                return False
            db.commit()
            return True
