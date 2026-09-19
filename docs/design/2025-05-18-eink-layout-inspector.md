# 墨水屏布局排版与 AI 可读会话反思机制设计文档

## 目标
在不修改墨水屏硬件端固件的前提下，重构与升级服务端布局排版测量系统，引入**墨水屏布局空间语义会话引擎 (AI-Readable Layout Inspector & Session Engine)**。在自动化生成与输出阶段，实时输出 AI 可直接读懂的物理几何分布、折行诊断、剩余预算与 ASCII 版面拓扑，建立“空间预算先验 -> 虚拟排版测量 -> AI 会话反馈与自愈”的闭环，彻底消除视觉截断与留白偏差。

## 背景与约束
1. **固件零改动**：设备端固件无法修改，墨水屏仍按现有的标准 HTTP 接口拉取 1-bit BMP 图片并上屏。
2. **墨水屏空间硬约束**：无滚动条，视窗物理像素固定（如 400x300、296x128、800x480）。文字过多会导致被底部安全线硬性截断，文字过少会导致下半部严重空旷。
3. **视觉偏差根因**：大模型生成内容时处于“盲盒”状态，缺乏像素级和字符级空间物理认知。
4. **解决方案**：在渲染测量管线中植入轻量级布局探针，将复杂的像素坐标抽象为标准 AI 可读会话（ASCII 视窗草图 + 物理空间预算 + 折行与截断诊断 + 调优建议），同时为 LLM 提供空间先验提示与自愈校准。

## 方案设计
1. **`core/layout_inspector.py`**：
   - 核心数据结构 `BlockInspection`、`LayoutSession`。
   - `inspect_layout(mode_def, content, screen_w, screen_h)`：执行虚拟排版度量，捕获各 Block 的 `[x, y, w, h]`、文本分行情况、单字孤行（Orphans）、溢出截断（Truncation）及剩余像素空间。
   - `format_ascii_preview(session)`：生成 40x15 等比例 ASCII 字符版面拓扑图，直观标记 `[StatusBar]`, `[Title]`, `[Body: N lines]`, `[Whitespace]`, `[Footer]`。
   - `format_ai_dialogue(session)`：将测量结果格式化为 AI 对话系统消息（`AI-Readable Context`），包含排版评分（Density Score）、告警详情与微调指引。
2. **自动化生成与自愈闭环 (`core/json_content.py` & `core/pipeline.py`)**：
   - 在向大模型发送 Prompt 前，根据目标分辨率自动注入 `Spatial Token Budget Hint`（如建议字数范围）。
   - 内容生成后，立即调用 Inspector 进行虚拟测量；若触发截断或严重失衡，自动进行字体尺寸降级回退（Auto font-stepping）或触发反思微调，确保产出位图 100% 完整。
3. **对外开放接口 (`api/routes/modes.py` & `api/routes/render.py`)**：
   - 新增 `GET /api/modes/{mode_id}/layout-session` 及在 `/api/preview` 中支持 `include_layout=1`。
   - 允许外部 Agent、Web 前端与自动化测试直接获取结构化会话与 ASCII 拓扑。

## 验收标准
1. `inspect_layout` 能准确捕获所有 Block 真实渲染坐标、分行情况与留白预算。
2. ASCII 视觉草图清晰呈现版面结构。
3. 超长文本模拟中，Inspector 能正确告警并识别截断。
4. 全量自动化单元测试与回归测试通过率 100%。
