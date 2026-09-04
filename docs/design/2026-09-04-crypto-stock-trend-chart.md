# 资产行情与股票趋势折线图 (Sparkline / Trend Chart) 架构设计

## 1. 目标
1. **硬件接口完全不变**：ESP32 墨水屏设备端拉取 `/api/render` 与 `/api/screen` 依旧输出符合屏幕物理规格的 1-bit / BWR 图像流；
2. **专属墨水屏折线图组件 (`sparkline` / `trend_chart`)**：
   - 在 `backend/core/json_renderer.py` 中注册 `sparkline` 块渲染器；
   - 专为墨水屏优化：
     - 清晰的平滑折线绘制（支持粗细 `line_width`，自适应高低范围）；
     - 参考基准横线（昨收基准虚线或高低参考线）；
     - 首尾关键点或最高/最低点圆点指示；
     - 多色阶支持：折线与端点支持配置为 `color: "red"`，在黑白红屏幕上极其亮眼。
3. **行情与股票数据模型升级 (`backend/core/providers/crypto_provider.py`)**：
   - 字段扩展：除了 `price`, `change_24h`, `high_24h`, `low_24h` 以外，新增 `sparkline_data` 数组（时间序列点）与 `trend_points`；
   - 支持加密资产（BTC, ETH, SOL 等）与全球股票/指数（AAPL 苹果, TSLA 特斯拉, NVDA 英伟达, 上证指数 等）；
   - 自动生成或拉取高品质 24 小时分时走势序列（16~32 个采样平滑点）；
4. **内置模式排版优化 (`crypto.json` / `en/crypto.json`)**：
   - 在大字价格与 24h 涨跌幅下方，嵌入优美的 `sparkline` 趋势折线图，底部保留最高价与最低价；
5. **前端适配与模拟渲染**：
   - 在 Web 端 `/preview` 与 `/config` 控制台中支持选择股票与加密货币代码，并在画布上即时呈现带有高保真趋势折线图的墨水屏排版。
