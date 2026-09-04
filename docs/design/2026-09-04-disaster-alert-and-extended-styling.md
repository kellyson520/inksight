# 自然灾害预警系统与多样化组件样式设计文档

## 目标
1. **构建墨水屏多样化排版样式组件库**：
   - 页眉系列：`header_banner`（全宽实心/反白横幅）、`header_compact`（极简带微状态横幅）
   - 页脚系列：`footer_ornate`（双细线花饰古典页脚）、`footer_badge`（胶囊状态页脚）
   - 花边与边框：`lace_border`（古典齿状/回纹花边框）、`corner_bracket`（四角几何艺术包角）、`double_border`（双重留白边框）
   - 12 大类自然灾害 E-Ink 矢量图标：台风、暴雨、暴雪、大风、高温、寒潮、地震、森林火险、海啸、冰雹、沙尘暴、大雾
2. **构建自然灾害预警系统 (Highest Priority Alert System)**：
   - 官方多源预警接入：和风天气官方气象预警 API (`/v7/warning/now`) + Open-Meteo 全球预警 + 预警级别映射 (红/橙/黄/蓝)；
   - 用户配置：支持设备级别开启 `disaster_alert` 预警监听，支持配置最低触发级别（如“仅红色/橙色”或“全部预警”）；
   - 最高优先级中断机制：当目标区域发生灾害预警且达到设定等级时，系统立即抢占所有普通模式（无论处于 cycle、time_slot 还是普通请求），强制展示紧急避险通报；
   - 即时主动推送：后台检测到新增灾害事件时，立刻渲染并注入 `_preview_push_queue`，标记 `pending_refresh=True`，设备无论何时请求均第一时间收到紧急警报。

---

## 模块划分与架构

```
                     ┌─────────────────────────────┐
                     │ QWeather / Open-Meteo Alerts│
                     └──────────────┬──────────────┘
                                    │
                       core/disaster_service.py
                      (预警抓取、缓存、级别与危害过滤)
                                    │
           ┌────────────────────────┴────────────────────────┐
           ▼                                                 ▼
    core/pipeline.py                               api/routes/render.py
(生成前进行最高优先级抢占检查)                         (即时推送队列与缓存绕过)
           │                                                 │
           └────────────────────────┬────────────────────────┘
                                    ▼
                         core/blocks/disaster.py
                         core/blocks/frames.py
                      core/blocks/headers_footers.py
```

### 1. 组件细化分文件存放 (`backend/core/blocks/`)
- `backend/core/blocks/headers_footers.py`:
  - `header_banner`: 全宽实心/反白条，左侧灾害等级/主分类，中间居中标题，右侧实时时间；
  - `header_compact`: 细线分隔，左侧小圆点/胶囊，右侧状态；
  - `footer_ornate`: 双线+中间菱形/星星点缀+双侧对齐文本；
  - `footer_badge`: 左侧胶囊药丸，右侧时间/版本；
- `backend/core/blocks/frames.py`:
  - `lace_border`: 绘制典雅复古边框/花边；
  - `corner_bracket`: 仅在四角绘制 L 型或倒角折角；
  - `double_border`: 绘制内外双线边框；
- `backend/core/blocks/disaster.py`:
  - `disaster_icon`: 针对 12 大类灾害纯手绘矢量位图/路径，黑白红三色鲜明辨识；
  - `disaster_banner`: 紧急大横幅，支持危险等级倒三角与粗黑警告线；
  - `disaster_advice_box`: 应急避险指南与防护措施盒子；

### 2. 灾害预警引擎 (`backend/core/disaster_service.py`)
- `fetch_active_alerts(lat, lon, city=None)`: 抓取当前活跃灾害预警；
- `check_device_disaster_alert(mac, cfg)`: 校验某设备是否有达到触发门槛的有效预警；
- `build_disaster_alert_mode_def(alert)`: 动态生成极具警示感的全屏墨水屏紧急预警 JSON mode 结构；
- `broadcast_disaster_alert(mac_list, alert)`: 批量写入推送队列并唤醒设备。

---

## 边界与防误报策略 (Guards & Boundaries)
- 警报有效期过期（超过 `endTime`）自动恢复普通模式，不永久卡死屏幕；
- 支持预警等级过滤（用户若选择 `orange`，则 `blue` 和 `yellow` 不打扰，仅 `orange` 与 `red` 抢占）；
- 严格遵循 E-Ink 三色对比度，确保警报文字在大雾、地震等恶劣环境下依然清晰可读。
