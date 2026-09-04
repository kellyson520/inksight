# 自然灾害预警系统与墨水屏多样化样式实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 扩充墨水屏页眉、页脚、古典/几何花边框与 12 类自然灾害矢量图标，接入气象灾害预警服务并在发生时以最高优先级中断当前所有模式进行全屏紧急推送。

**Architecture:** 
- 渲染层：在 `core/blocks/` 下细分 `headers_footers.py`、`frames.py`、`disaster.py`，注册现代 E-Ink 原生组件；
- 领域层：在 `core/disaster_service.py` 整合官方气象预警 API、等级严重度过滤与缓存；
- 调度层：在 `core/pipeline.py` 与 `api/routes/render.py` 植入最高优先级抢占守卫（Preemptive Disaster Alert Guard），有生效灾害警报时立刻抢占渲染，并通过推送队列即时唤醒设备下发。

**Tech Stack:** Python 3.10+, FastAPI, Pillow (PIL), pytest, httpx, SQLite.
**Spec:** `docs/design/2026-09-04-disaster-alert-and-extended-styling.md`

## Global Constraints
- 所有新增组件必须支持 1-bit（黑白）与 2-bit/3-color（黑白红）调色板，红色通道用于高警示灾害要素；
- 必须保持 100% 向后兼容，历史模式渲染不受影响；
- 预警解除或超时后自适应无缝恢复常规模式。

---

### Task 1: 实现多样化页眉与页脚组件 (`backend/core/blocks/headers_footers.py`)
- `header_banner`: 全宽实心或反白横幅
- `header_compact`: 紧凑型点缀页眉
- `footer_ornate`: 欧式/古典双线居中菱形页脚
- `footer_badge`: 胶囊式数据与版本页脚

### Task 2: 实现花边、包角与双重线边框组件 (`backend/core/blocks/frames.py`)
- `lace_border`: 欧式古典回纹与齿状花边框
- `corner_bracket`: 四角 L 型或几何折角
- `double_border`: 外粗内细或双细线留白框架

### Task 3: 实现 12 大类自然灾害 E-Ink 图标与避险卡片 (`backend/core/blocks/disaster.py`)
- 矢量绘制 12 种灾害图标：台风、暴雨、暴雪、大风、高温、寒潮、地震、森林火险、海啸、冰雹、沙尘暴、大雾
- `disaster_icon`, `disaster_banner`, `disaster_advice_box` 组件

### Task 4: 实现自然灾害预警服务 (`backend/core/disaster_service.py`)
- QWeather / Open-Meteo 灾害预警接口获取与数据解析
- 预警等级判定（红/橙/黄/蓝）与缓存
- 构造最高优先级预警 JSON 布局模板

### Task 5: 管道最高优先级抢占与即时推送 (`backend/core/pipeline.py`, `backend/api/routes/render.py`)
- 检查设备配置 `disaster_alert`
- 命中预警时绕过常规 mode 直接抢占
- 注入 `_preview_push_queue` 并设置 `pending_refresh=True`

### Task 6: 设备预警配置与测试端点 (`backend/api/routes/device.py`)
- 新增 `POST /api/device/{mac}/disaster-alert/simulate` 供用户测试灾害强推效果
- 丰富设备设置 schema

### Task 7: 自动化测试与 OCR 视觉验证 (`backend/tests/test_disaster_and_frames.py`)
- 编写测试用例覆盖全部新组件与预警抢占逻辑
- 视觉碰撞分析验证
