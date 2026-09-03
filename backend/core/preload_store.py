"""
服务端多天数据预存与滚动推送模块 (Preload Store)
为墨水屏提供抗 LLM 网络抖动、抗 API 超额与零等待的本地缓冲池机制。
支持：
1. 历史上的今天 (THISDAY): 预存多天 (如今天及未来7~14天)，按天精确滚动；
2. 每日一句 (DAILY / MY_QUOTE / STOIC): 滚动名言金句缓冲池；
3. 每日一词 (WORD_OF_THE_DAY): 滚动学习词汇缓冲池；
"""
from __future__ import annotations

import hashlib
import json
import logging
from datetime import date, timedelta
from typing import Any, Optional

from .db import get_main_db

logger = logging.getLogger(__name__)

# 表初始化 SQL
_CREATE_PRELOAD_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS content_preload_pool (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    mode_id       TEXT    NOT NULL,
    target_date   TEXT    DEFAULT '',
    content_json  TEXT    NOT NULL,
    content_hash  TEXT    NOT NULL,
    quality_score INTEGER DEFAULT 100,
    used_count    INTEGER DEFAULT 0,
    created_at    TEXT    NOT NULL DEFAULT (datetime('now'))
);
"""

_CREATE_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_preload_mode_date ON content_preload_pool(mode_id, target_date);
"""

# 设备滚动索引表（记录某个设备在某个模式/某一天消费到的预存游标）
_CREATE_DEVICE_PRELOAD_STATE_SQL = """
CREATE TABLE IF NOT EXISTS device_preload_state (
    mac           TEXT    NOT NULL,
    mode_id       TEXT    NOT NULL,
    target_date   TEXT    DEFAULT '',
    cursor_idx    INTEGER DEFAULT 0,
    updated_at    TEXT    NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (mac, mode_id, target_date)
);
"""


async def init_preload_db() -> None:
    """幂等初始化预存表。"""
    db = await get_main_db()
    await db.execute(_CREATE_PRELOAD_TABLE_SQL)
    await db.execute(_CREATE_INDEX_SQL)
    await db.execute(_CREATE_DEVICE_PRELOAD_STATE_SQL)
    await db.commit()


def _compute_hash(content: dict[str, Any]) -> str:
    serialized = json.dumps(content, sort_keys=True, ensure_ascii=False)
    return hashlib.md5(serialized.encode("utf-8")).hexdigest()


async def add_preload_item(
    mode_id: str,
    content: dict[str, Any],
    target_date: str = "",
    quality_score: int = 100,
) -> bool:
    """向预存池写入一条数据。如果哈希已存在则忽略。"""
    c_hash = _compute_hash(content)
    db = await get_main_db()
    try:
        cursor = await db.execute(
            "SELECT id FROM content_preload_pool WHERE mode_id = ? AND content_hash = ?",
            (mode_id.upper(), c_hash),
        )
        if await cursor.fetchone():
            return False

        await db.execute(
            """
            INSERT INTO content_preload_pool (mode_id, target_date, content_json, content_hash, quality_score)
            VALUES (?, ?, ?, ?, ?)
            """,
            (mode_id.upper(), target_date, json.dumps(content, ensure_ascii=False), c_hash, quality_score),
        )
        await db.commit()
        return True
    except Exception as exc:
        logger.warning("[Preload] Failed to add item for %s: %s", mode_id, exc)
        return False


async def get_next_preload_item(
    mode_id: str,
    mac: str = "",
    target_date: str = "",
) -> Optional[dict[str, Any]]:
    """从预存池中按设备游标获取下一条内容（支持按天滚动与平滑循环）。"""
    mode_id = mode_id.upper()
    clean_mac = (mac or "DEFAULT").upper()
    db = await get_main_db()

    # 1. 查找匹配的预存列表
    if target_date:
        cursor = await db.execute(
            "SELECT id, content_json FROM content_preload_pool WHERE mode_id = ? AND target_date = ? ORDER BY id ASC",
            (mode_id, target_date),
        )
        rows = await cursor.fetchall()
        if not rows:
            # 回退到无特定日期的通用预存池
            cursor = await db.execute(
                "SELECT id, content_json FROM content_preload_pool WHERE mode_id = ? AND target_date = '' ORDER BY id ASC",
                (mode_id,),
            )
            rows = await cursor.fetchall()
    else:
        cursor = await db.execute(
            "SELECT id, content_json FROM content_preload_pool WHERE mode_id = ? ORDER BY id ASC",
            (mode_id,),
        )
        rows = await cursor.fetchall()

    if not rows:
        return None

    # 2. 获取设备当前游标
    query_date_key = target_date if target_date else "ALL"
    c_cursor = await db.execute(
        "SELECT cursor_idx FROM device_preload_state WHERE mac = ? AND mode_id = ? AND target_date = ?",
        (clean_mac, mode_id, query_date_key),
    )
    row = await c_cursor.fetchone()
    current_idx = row[0] if row else 0

    chosen_row = rows[current_idx % len(rows)]
    next_idx = current_idx + 1

    # 3. 更新游标和使用计数
    await db.execute(
        """
        INSERT INTO device_preload_state (mac, mode_id, target_date, cursor_idx, updated_at)
        VALUES (?, ?, ?, ?, datetime('now'))
        ON CONFLICT(mac, mode_id, target_date) DO UPDATE SET
            cursor_idx = excluded.cursor_idx,
            updated_at = excluded.updated_at
        """,
        (clean_mac, mode_id, query_date_key, next_idx),
    )
    await db.execute(
        "UPDATE content_preload_pool SET used_count = used_count + 1 WHERE id = ?",
        (chosen_row[0],),
    )
    await db.commit()

    try:
        content = json.loads(chosen_row[1])
        content["_from_preload"] = True
        return content
    except Exception:
        return None


async def get_preload_count(mode_id: str, target_date: str = "") -> int:
    """查询指定模式和日期的预存条数。"""
    db = await get_main_db()
    if target_date:
        cursor = await db.execute(
            "SELECT COUNT(*) FROM content_preload_pool WHERE mode_id = ? AND target_date = ?",
            (mode_id.upper(), target_date),
        )
    else:
        cursor = await db.execute(
            "SELECT COUNT(*) FROM content_preload_pool WHERE mode_id = ?",
            (mode_id.upper(),),
        )
    row = await cursor.fetchone()
    return row[0] if row else 0
