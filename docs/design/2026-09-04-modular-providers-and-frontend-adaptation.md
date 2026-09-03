# 开放内容源模块化插件体系与全端适配设计

## 1. 目标
1. **硬件接口零改动**：保持 `/api/render` 与 `/api/screen` 契约不变；
2. **后端 Provider 模块化解耦**：将原来散落在 `json_content.py` 中冗长 `if provider == "xxx"` 的代码重构为独立的模块化插件目录 `backend/core/providers/`；
   - 每个 Provider 实现统一接口：`async def generate(mode_def, content_cfg, fallback, **kwargs) -> dict`
   - 核心内置模块：
     - `providers/rss_provider.py`：RSS/Atom 订阅源模块
     - `providers/crypto_provider.py`：加密货币/股票行情 Ticker 模块（支持 BTC, ETH, SOL, DOGE 等实时价格、涨跌幅、24h 高低点与走势模拟图）
     - `providers/quote_provider.py`：语录与哲学金句模块（含预存池无缝消费与滚动）
     - `providers/thisday_provider.py`：历史今日模块（含跨多天滚动与本地预存消费）
     - `providers/webhook_provider.py`：Open Webhook / 自定义开放数据模块
3. **注册中心机制**：`ProviderRegistry` 统一注册与按名分发，支持轻松扩充新玩法；
4. **前端配置与预览全面适配**：
   - 预览控制台 (`/preview`)：支持 RSS、CRYPTO 行情等模块的专属配置弹窗与快捷预设；
   - 设备配置中心 (`/config`)：通过模式自身的 `settings_schema` 自动渲染表单，并支持保存到设备配置；
5. **预存与离线保障**：预存池机制覆盖所有开放模式，断网/离线依然优雅显示。
