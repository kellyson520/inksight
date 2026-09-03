# 服务端多天数据预存与滚动推送机制架构设计 (Preload Store)

## 1. 背景与目标
在墨水屏实际使用中，LLM API 存在网络抖动、提供商配额超限、响应超时（耗时 3~10 秒导致墨水屏 WiFi 保持连接功耗剧增）等问题。
**目标**：
- 在服务端构建轻量、高效的**预存数据池（Preload Store）**；
- 支持模式：
  1. **历史上的今天 (THISDAY)**：支持按当前日期及未来 7~14 天滚动预存（每天 3~5 条真实历史大事记），每天自动根据 `YYYY-MM-DD` 匹配当天的历史事件，同天内支持多轮游标循环；
  2. **每日一句 (DAILY / MY_QUOTE / STOIC)**：预存优质名言金句缓冲池（数十条），按设备维度防重轮换；
  3. **每日一词 (WORD_OF_THE_DAY)**：预存精选词汇与例句库，按设备防重轮换；
- **生成链路优化**：
  - 当设备请求到达时，优先直接从本地预存库毫秒级取出当天的优质数据进行排版，**彻底摆脱对外网 LLM / API 的实时依赖**；
  - 若配置了强制 LLM 生成或预存耗尽，自动降级调用 LLM 并将新内容异步回填入预存库；
  - 零破坏：硬件端点 `/api/render` 与图片契约不变，功耗降低（设备不用等待数秒 LLM 调用）。

## 2. 数据库表设计 (`backend/core/preload_store.py`)
```sql
CREATE TABLE IF NOT EXISTS content_preload_pool (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    mode_id       TEXT    NOT NULL,
    target_date   TEXT    DEFAULT '',    -- 'YYYY-MM-DD' 或空（通用池）
    content_json  TEXT    NOT NULL,
    content_hash  TEXT    NOT NULL,
    quality_score INTEGER DEFAULT 100,
    used_count    INTEGER DEFAULT 0,
    created_at    TEXT    NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_preload_mode_date ON content_preload_pool(mode_id, target_date);
```

## 3. 设备滚动状态管理
在设备状态中记录 `preload_cursor_{mode_id}` 或利用 `stats_store` 已有的 `content_history` 防重记录，确保：
1. 历史上的今天：严格按照今天的自然日 `date.today()` 读取当天的预存事件，同一天内的多次刷新循环展示当天不同的大事；跨天时自动切入下一天的预存大事，连滚 7 天及更久；
2. 金句 / 单词：每刷新一次顺延游标并记录到设备历史，实现平滑滚动。
