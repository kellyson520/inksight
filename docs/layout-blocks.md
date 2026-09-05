# InkSight 底层排版组件与模式开发说明手册

本文档全面梳理 InkSight 墨水屏专用的底层排版组件体系（E-Ink Layout Blocks），详细说明各组件的数据规范、参数配置、代码示例与实际渲染配图效果，方便快速定制与扩展新的屏幕模式。

---

## 目录

1. [排版设计规范与限制](#1-排版设计规范与限制)
2. [新增极客高密度组件 (Geek Widgets)](#2-新增极客高密度组件-geek-widgets)
   - [2.1 stat_progress_bar (双端统计进度条)](#21-stat_progress_bar-双端统计进度条)
   - [2.2 pill_tag_list (自适应胶囊标签云)](#22-pill_tag_list-自适应胶囊标签云)
   - [2.3 code_snippet_box (极客终端代码卡片)](#23-code_snippet_box-极客终端代码卡片)
3. [事件与感知插播组件 (Monitoring & Alerts)](#3-事件与感知插播组件-monitoring--alerts)
   - [3.1 alert_callout (变动与预警通知横幅)](#31-alert_callout-变动与预警通知横幅)
   - [3.2 change_diff_card (新旧版本内容差分卡片)](#32-change_diff_card-新旧版本内容差分卡片)
   - [3.3 timeline_event (时间线事件节点)](#33-timeline_event-时间线事件节点)
4. [时序与图表组件 (Charts & Media)](#4-时序与图表组件-charts--media)
   - [4.1 sparkline_chart (高密度金融走势折线)](#41-sparkline_chart-高密度金融走势折线)
   - [4.2 image (本地/远程图像与书封)](#42-image-本地远程图像与书封)
5. [综合实战模式范例与配图](#5-综合实战模式范例与配图)

---

## 1. 排版设计规范与限制

- **严禁使用 Emoji**：墨水屏仅支持 1-bit 黑白或三色/四色（黑白红黄），Emoji 渲染会导致字形回退或出现乱码方块，一律使用英文字符、符号（如 `·`、`>`、`#`）或内置矢量图标。
- **自动度量机制**：所有 block 都必须在 `core/blocks/measure.py` 中声明自身的高度测量规则，确保 flex_row、two_column 及页面滚动高度精确计算，绝不允许溢出到底栏横线之外。
- **高对比度优先**：细线推荐 `1px`，卡片外框必须包含明确的描边（outline）或反色实心（solid）。

---

## 2. 新增极客高密度组件 (Geek Widgets)

### 2.1 stat_progress_bar (双端统计进度条)
专为硬件资源占用率、技术热度分值或任务进度打造的进度条，顶端紧凑展示「左端项目名称」与「右端百分比及明细数值」，底部为圆角外框槽线与比例填充。

#### JSON 配置示例
```json
{
  "type": "stat_progress_bar",
  "label": "热度指数",
  "value_field": "trend_score",
  "max_value": 100,
  "unit": "PTS",
  "margin_x": 12,
  "height": 6,
  "show_percent": true,
  "margin_bottom": 6
}
```

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `label` | string | 否 | 左端标题文字，支持模板替换 |
| `value_field` | string | 是 | 当前数值字段（支持整数或浮点数） |
| `max_value` | number | 否 | 最大值，默认 100.0 |
| `unit` | string | 否 | 右端数值单位（如 `PTS`、`GB`、`%`） |
| `height` | number | 否 | 进度槽高度像素，默认 7 |
| `margin_x` | number | 否 | 水平左右边距，默认 14 |
| `color` | string | 否 | 进度条填充颜色（`red` 为四色红，缺省为黑） |

---

### 2.2 pill_tag_list (自适应胶囊标签云)
根据屏幕剩余可用宽度，自动流式折行排列的胶囊标签组。支持实心反色与空心描边两种形态，适合技术栈、分类 Tag、关键词高密度展示。

#### JSON 配置示例
```json
{
  "type": "pill_tag_list",
  "field": "tags",
  "margin_x": 12,
  "font_size": 9,
  "variant": "outline",
  "gap_x": 6,
  "gap_y": 5,
  "margin_bottom": 6
}
```

| 参数 | 类型 | 说明 |
|---|---|---|
| `field` | string | 包含标签字符串数组的字段（如 `["Rust", "Docker", "Go"]`） |
| `variant` | string | `outline`（空心线框黑字）或 `solid`（黑底反白字） |
| `font_size` | number | 标签字体大小，默认 10 |
| `padding_x` / `padding_y` | number | 胶囊内边距 |

---

### 2.3 code_snippet_box (极客终端代码卡片)
拟真 Unix 终端窗口设计，包含顶部反色标题栏、三圆点控制台圆圈，以及下方等宽代码/配置行输出，具备自动超宽截断与行间距优化。

#### JSON 配置示例
```json
{
  "type": "code_snippet_box",
  "title_field": "snippet_title",
  "field": "code_snippet",
  "margin_x": 12,
  "font_size": 9,
  "margin_bottom": 4
}
```

---

## 3. 事件与感知插播组件 (Monitoring & Alerts)

### 3.1 alert_callout (变动与预警通知横幅)
带左侧高亮强调边框、等级 Tag 徽章与粗体通报标题的通知横幅，适用于紧急变动与灾害抢占插播。

```json
{
  "type": "alert_callout",
  "title": "网页变动感知通报",
  "level": "warning",
  "tag": "WEB WATCHER",
  "margin_x": 12,
  "margin_bottom": 8
}
```

### 3.2 change_diff_card (新旧版本内容差分卡片)
结构化对比两段文本的演进：上一状态显示在虚线灰底框中，更新后的新状态显示在粗实线强调框中，带“NEW”标记。

```json
{
  "type": "change_diff_card",
  "margin_x": 12,
  "prev_field": "prev_snippet",
  "new_field": "new_snippet",
  "margin_bottom": 8
}
```

### 3.3 timeline_event (时间线事件节点)
带有圆形节点与垂直连接线的时间轴条目，适合呈现变更日志、构建记录或部署流水线。

---

## 4. 时序与图表组件 (Charts & Media)

### 4.1 sparkline_chart (高密度金融走势折线)
支持 24 点日内走势高平滑贝塞尔曲线渲染、最高/最低极值虚线标定、振幅区域填充与红绿涨跌联动。

```json
{
  "type": "sparkline_chart",
  "field": "sparkline_data",
  "height": 72,
  "margin_x": 14,
  "show_extremes": true,
  "line_width": 2
}
```

### 4.2 image (本地/远程图像与书封)
自适应比例缩放与墨水屏二值化/抖动渲染，支持在 `two_column` 中与文本图文并茂并排。

```json
{
  "type": "image",
  "url_field": "cover_url",
  "width": 115,
  "height": 160,
  "fit": "contain",
  "dither": true
}
```

---

## 5. 综合实战模式范例与配图

以下均为通过真实 InkSight 渲染管线输出的 400×300 实际渲染预览效果：

### 5.1 极客科技雷达 (`TECH_RADAR`)
综合运用了 `stat_progress_bar` + `pill_tag_list` + `code_snippet_box`：

![TECH_RADAR 效果图](../images/blocks/tech_radar_preview.png)

### 5.2 网页变更感知通报 (`WEB_NOTICE`)
综合运用了 `alert_callout` + `change_diff_card` 差分卡片：

![WEB_NOTICE 效果图](../images/blocks/web_notice_preview.png)

### 5.3 黄金与现货趋势走势 (`GOLD`)
综合运用了双指标对比与 `sparkline_chart` 极值折线：

![GOLD 效果图](../images/blocks/gold_preview.png)

### 5.4 微信读书精选推荐 (`WECHAT_READ`)
综合运用了 `two_column` 图文绕排与 `image` 封面自适应居中对齐：

![WECHAT_READ 效果图](../images/blocks/wechat_read_preview.png)

### 5.5 国家标准四级自然灾害预警 (`DISASTER_ALERT`)
最高优先级抢占插播，运用矢量预警图标、等级仪表卡与防御指南：

![DISASTER_ALERT 效果图](../images/blocks/disaster_alert_preview.png)
