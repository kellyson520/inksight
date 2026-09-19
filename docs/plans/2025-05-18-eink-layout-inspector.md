# 墨水屏布局排版与 AI 可读会话反思机制实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建立墨水屏布局空间语义反思引擎，生成 AI 可读的布局诊断会话与 ASCII 空间草图，实现自动化排版防偏差闭环，保持固件零修改。

**Architecture:** 
- `backend/core/layout_inspector.py`: 核心测量探针、ASCII 字符拓扑生成器与 AI 对话格式化器。
- `backend/core/json_renderer.py`: 与 RenderContext 无缝集成布局信息收集。
- `backend/core/json_content.py`: 引入屏幕物理空间字数先验与超界自愈。
- `backend/api/routes/modes.py`: 提供 `/api/modes/{mode_id}/layout-session` 供 AI 与前端观测。

**Tech Stack:** Python 3.10, FastAPI, Pillow (PIL), pytest

## Global Constraints
- 设备端固件不作任何代码变更。
- 保证既有 JSON 模式定义格式完全向下兼容。
- 零额外外部重依赖，基于 Pillow 原生字体测量。

---

### Task 1: 核心布局探针与会话格式化器 (`backend/core/layout_inspector.py`)
- [ ] 编写失败测试 `backend/tests/test_layout_inspector.py`
- [ ] 运行测试确认失败
- [ ] 实现 `backend/core/layout_inspector.py`（包含 `inspect_layout`, `format_ascii_preview`, `format_ai_dialogue`）
- [ ] 运行测试确认通过

### Task 2: 渲染器挂载与真实测量闭环 (`backend/core/json_renderer.py`)
- [ ] 编写渲染器集成测试 `test_renderer_layout_inspection`
- [ ] 运行测试确认失败
- [ ] 在 `render_json_mode` 中暴露或返回 `layout_session` 探针数据
- [ ] 运行测试确认通过

### Task 3: 自动化内容生成空间先验与防截断自愈 (`backend/core/json_content.py`)
- [ ] 编写空间字数限制先验与溢出自愈测试
- [ ] 在 `json_content.py` 中为 LLM 生成过程注入目标物理分辨率预算提示，并集成溢出自动平滑纠正
- [ ] 运行测试确认通过

### Task 4: 新增布局会话端点与 API 暴露 (`backend/api/routes/modes.py`)
- [ ] 编写 API 接口测试 `test_layout_session_endpoint`
- [ ] 在 `modes.py` 中添加 `GET /api/modes/{mode_id}/layout-session` 路由
- [ ] 运行测试确认通过

### Task 5: 全量回归测试、WebApp 构建、Docker 热更与代码提交
- [ ] 运行完整 pytest 矩阵，确保全部通过无回归
- [ ] 构建 WebApp (`npm run build`) 确认零报错
- [ ] 重启生产 Docker 容器并验证实机 HTTP 渲染与布局会话 API
- [ ] 提交代码并推送至 Git 仓库
