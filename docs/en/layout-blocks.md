# InkSight Layout Blocks & Standalone Visual Spec

This guide documents the standalone visual appearance, parameters, and configuration of each low-level layout block. **Every block is presented with its own isolated rendering snapshot** without surrounding container distractions.

---

## Table of Contents

1. [General Constraints](#1-general-constraints)
2. [Geek Widgets](#2-geek-widgets)
   - [2.1 stat_progress_bar](#21-stat_progress_bar)
   - [2.2 pill_tag_list](#22-pill_tag_list)
   - [2.3 code_snippet_box](#23-code_snippet_box)
3. [Monitoring & Alerts](#3-monitoring--alerts)
   - [3.1 alert_callout](#31-alert_callout)
   - [3.2 change_diff_card](#32-change_diff_card)
   - [3.3 timeline_event](#33-timeline_event)
4. [Charts & Metrics](#4-charts--metrics)
   - [4.1 sparkline](#41-sparkline)
   - [4.2 metric_card](#42-metric_card)
   - [4.3 disaster_level_meter](#43-disaster_level_meter)

---

## 1. General Constraints

- **Zero Emoji Policy**: E-ink displays operate on 1-bit or 4-color palettes. Emojis cause font fallbacks or garbled glyph boxes. Use clean ASCII symbols (`·`, `>`, `#`) or vector icons instead.
- **Isolated Snapshot Rule**: Each component snapshot below is rendered in isolation on a clean canvas to exhibit its internal padding, borders, and typography.

---

## 2. Geek Widgets

### 2.1 stat_progress_bar
Displays metric progress with a top label and value percentage, backed by a rounded progress groove with proportional fill.

#### Standalone Snapshot
![stat_progress_bar](../../images/blocks/individual/stat_progress_bar.png)

#### JSON Configuration
```json
{
  "type": "stat_progress_bar",
  "label": "CPU Load",
  "value_field": "val",
  "max_value": 100,
  "unit": "PCT",
  "margin_x": 10,
  "height": 8,
  "show_percent": true,
  "margin_bottom": 4
}
```

---

### 2.2 pill_tag_list
Flowing capsule tags cloud that automatically wraps based on remaining container width.

#### Standalone Snapshot
![pill_tag_list](../../images/blocks/individual/pill_tag_list.png)

#### JSON Configuration
```json
{
  "type": "pill_tag_list",
  "field": "tags",
  "margin_x": 10,
  "font_size": 11,
  "variant": "outline",
  "gap_x": 8,
  "gap_y": 6,
  "margin_bottom": 4
}
```

---

### 2.3 code_snippet_box
Terminal-inspired window with a three-dot header titlebar and monospace code lines.

#### Standalone Snapshot
![code_snippet_box](../../images/blocks/individual/code_snippet_box.png)

#### JSON Configuration
```json
{
  "type": "code_snippet_box",
  "title": "deploy.sh",
  "field": "code",
  "margin_x": 10,
  "font_size": 10,
  "margin_bottom": 4
}
```

---

## 3. Monitoring & Alerts

### 3.1 alert_callout
High-priority notification banner with accent border and level tags.

#### Standalone Snapshot
![alert_callout](../../images/blocks/individual/alert_callout.png)

```json
{
  "type": "alert_callout",
  "title": "Detected critical system config change",
  "level": "warning",
  "tag": "MONITOR",
  "margin_x": 10,
  "margin_bottom": 4
}
```

---

### 3.2 change_diff_card
Side-by-side or stacked diff card highlighting PREVIOUS state vs NEW updated state.

#### Standalone Snapshot
![change_diff_card](../../images/blocks/individual/change_diff_card.png)

```json
{
  "type": "change_diff_card",
  "prev_field": "prev",
  "new_field": "new",
  "margin_x": 10,
  "margin_bottom": 4
}
```

---

### 3.3 timeline_event
Timestamped event node on a vertical timeline axis with line connection and dot bullet.

#### Standalone Snapshot
![timeline_event](../../images/blocks/individual/timeline_event.png)

```json
{
  "type": "timeline_event",
  "time": "16:45",
  "content": "Master-slave sync complete, replica ready",
  "status": "success",
  "margin_x": 10,
  "margin_bottom": 2
}
```

---

## 4. Charts & Metrics

### 4.1 sparkline
24-point intraday financial trendline with extreme value guides and area filling.

#### Standalone Snapshot
![sparkline](../../images/blocks/individual/sparkline.png)

```json
{
  "type": "sparkline",
  "field": "pts",
  "height": 64,
  "margin_x": 10,
  "show_extremes": true,
  "line_width": 2,
  "margin_bottom": 4
}
```

---

### 4.2 metric_card
Primary prominent metric card with high-contrast borders and subordinate change badges.

#### Standalone Snapshot
![metric_card](../../images/blocks/individual/metric_card.png)

```json
{
  "type": "metric_card",
  "title": "Gold Benchmark Price",
  "value_field": "price",
  "sub_value_field": "chg",
  "margin_x": 10,
  "height": 56,
  "margin_bottom": 4
}
```

---

### 4.3 disaster_level_meter
National 4-tier emergency disaster warning gauge.

#### Standalone Snapshot
![disaster_level_meter](../../images/blocks/individual/disaster_level_meter.png)

```json
{
  "type": "disaster_level_meter",
  "level": "orange",
  "disaster_type": "rainstorm",
  "margin_x": 10,
  "margin_bottom": 4
}
```
