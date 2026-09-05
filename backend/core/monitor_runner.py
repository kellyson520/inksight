"""Periodic runner for web monitor targets."""
from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
from typing import Any

logger = logging.getLogger(__name__)


class MonitorRunner:
    def __init__(
        self,
        service: Any,
        *,
        now: Callable[[], float] = time.time,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
        poll_interval: float = 30.0,
    ) -> None:
        self.service = service
        self.now = now
        self.sleep = sleep
        self.poll_interval = max(0.0, poll_interval)
        self._stopped = False

    def stop(self) -> None:
        self._stopped = True

    def _is_due(self, target: dict[str, Any]) -> bool:
        if not target.get("enabled", True):
            return False
        interval = max(1.0, float(target.get("check_interval", 300)))
        last_checked = float(target.get("last_checked") or 0)
        return self.now() - last_checked >= interval

    async def run_once(self) -> int:
        checked = 0
        for target in self.service.list_targets():
            if not self._is_due(target):
                continue
            try:
                await self.service.check_target(target)
            except Exception:
                logger.exception("[MonitorRunner] target check failed: %s", target.get("id"))
            checked += 1
        return checked

    async def run_forever(self) -> None:
        self._stopped = False
        while not self._stopped:
            await self.run_once()
            await self.sleep(self.poll_interval)
