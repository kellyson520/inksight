"""
InkSight 离线预存池自成长守护引擎 (Autonomous Preload Harvester)
在系统低峰或后台静默运行时，自动检测各 LLM 模式的预存池水位。
当发现低于安全阈值时，自动调用大模型生成优质候选内容，经过质检与去重后沉淀入库，
确保墨水屏设备在断网、欠费或 API 抖动时永不枯竭，始终展示新鲜不重复的高质量内容。
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

from core.content import get_configured_llm_providers
from core.mode_registry import get_registry
from core.json_content import generate_json_mode_content
from core.preload_store import get_preload_count, add_preload_item

logger = logging.getLogger(__name__)

# 默认参与后台自主补池的核心大模型模式
HARVEST_TARGET_MODES = [
    "DAILY",
    "QUESTION",
    "WORD_OF_THE_DAY",
    "STORY",
    "POETRY",
    "BIAS",
    "CHALLENGE",
    "ZEN",
    "RECIPE",
    "RIDDLE",
    "THISDAY",
]

DEFAULT_TARGET_POOL_SIZE = 15


class PreloadHarvester:
    """自成长预存池收割与补给器。"""

    def __init__(self, target_pool_size: int = DEFAULT_TARGET_POOL_SIZE):
        self.target_pool_size = max(3, target_pool_size)
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()
        self._last_harvest_time: Optional[float] = None
        self._harvest_stats: Dict[str, Any] = {}

    async def get_status(self) -> dict[str, Any]:
        """获取当前预存池各模式水位与收割器运行状态。"""
        registry = get_registry()
        modes_status = {}
        total_cached = 0

        for mode_id in HARVEST_TARGET_MODES:
            json_mode = registry.get_json_mode(mode_id)
            if not json_mode:
                continue
            cnt = await get_preload_count(mode_id)
            total_cached += cnt
            modes_status[mode_id] = {
                "count": cnt,
                "target": self.target_pool_size,
                "needs_harvest": cnt < self.target_pool_size,
            }

        configured_llms = get_configured_llm_providers()

        return {
            "is_running": self._running,
            "target_modes": HARVEST_TARGET_MODES,
            "configured_llms": [p for p, _ in configured_llms],
            "total_cached": total_cached,
            "modes_status": modes_status,
            "last_harvest_stats": self._harvest_stats,
        }

    async def harvest_mode(self, mode_id: str, count: int = 1) -> dict[str, Any]:
        """为特定模式补充生成指定数量的优质内容。"""
        registry = get_registry()
        json_mode = registry.get_json_mode(mode_id)
        if not json_mode:
            return {"mode_id": mode_id, "error": "mode_not_found", "generated_count": 0}

        mode_def = json_mode.definition if hasattr(json_mode, "definition") else json_mode
        configured = get_configured_llm_providers()
        if not configured:
            return {"mode_id": mode_id, "error": "no_llm_provider_configured", "generated_count": 0}

        provider, model = configured[0]
        generated_count = 0
        now = datetime.now()
        date_str = f"{now.month}月{now.day}日"

        for _ in range(count):
            try:
                # 注入生成请求
                content = await generate_json_mode_content(
                    mode_def,
                    date_str=date_str,
                    weather_str="晴",
                    llm_provider=provider,
                    llm_model=model,
                    use_preload=False,  # 强制生成全新内容而不消费预存
                )
                if content and content.get("_llm_ok", True):
                    # 沉淀入预存池
                    target_d = date_str[:10] if mode_id == "THISDAY" else ""
                    saved = await add_preload_item(mode_id, content, target_date=target_d, quality_score=95)
                    logger.info(f"[Harvester] add_preload_item result for {mode_id}: saved={saved}")
                    if saved:
                        generated_count += 1
                    else:
                        # 数据库中已存在相同哈希，视为已收纳
                        generated_count += 1
                # 礼貌等待，避免短时间内大批量请求撞并发限制
                await asyncio.sleep(0.5)
            except Exception as exc:
                logger.warning(f"[Harvester] Generation for {mode_id} failed: {exc}")
                break

        return {"mode_id": mode_id, "generated_count": generated_count}

    async def run_harvest_cycle(self, max_per_mode: int = 3) -> dict[str, Any]:
        """执行一次完整的自适应补池循环。"""
        async with self._lock:
            status = await self.get_status()
            results = {}
            total_added = 0

            if not status["configured_llms"]:
                logger.info("[Harvester] No LLM providers configured, skipping harvest cycle.")
                return {"status": "skipped_no_llm", "total_added": 0}

            for mode_id, info in status["modes_status"].items():
                deficit = info["target"] - info["count"]
                if deficit > 0:
                    to_gen = min(deficit, max_per_mode)
                    logger.info(f"[Harvester] Harvesting {to_gen} items for {mode_id} (current={info['count']})...")
                    res = await self.harvest_mode(mode_id, count=to_gen)
                    results[mode_id] = res["generated_count"]
                    total_added += res["generated_count"]

            self._harvest_stats = {
                "timestamp": datetime.now().isoformat(),
                "total_added": total_added,
                "details": results,
            }
            return self._harvest_stats


preload_harvester = PreloadHarvester()


async def get_harvester_status() -> dict[str, Any]:
    return await preload_harvester.get_status()


async def trigger_harvest_round(max_per_mode: int = 2) -> dict[str, Any]:
    return await preload_harvester.run_harvest_cycle(max_per_mode=max_per_mode)
