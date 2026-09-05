# 自定义模式开发指南

InkSight 使用纯 JSON 配置来定义和扩展内容模式。

## 1. 设计原则

- 内容生成与布局渲染解耦
- 配置驱动，减少硬编码
- 新增模式优先复用现有 block 与 content type

## 2. 基本结构

一个模式定义通常包含：

- `mode_id` / `display_name` / `icon`
- `content`（生成逻辑）
- `layout`（渲染结构）
- `cacheable` / `description`

## 3. 常见 content.type

- `llm`：文本输出
- `llm_json`：结构化 JSON 输出
- `computed`：基于本地上下文计算
- `external_data`：外部数据源聚合
- `image_gen`：图像生成
- `composite`：组合多个子内容

## 4. 开发流程建议

1. 在 `backend/core/modes/builtin` 或 `custom` 下新增 json
2. 按 schema 校验字段合法性
3. 在预览接口验证渲染效果
4. 补齐测试（内容生成、渲染、路由）
5. 更新 README 与 docs

## 6. 底层排版组件全景

墨水屏原生支持丰富的声明式排版块，详见专用手册：
- [完整底层排版组件手册与配图](./layout-blocks.md)

常用高频组件速查：
- `stat_progress_bar`: 双端统计与任务进度条
- `pill_tag_list`: 自适应流式胶囊标签组
- `code_snippet_box`: 终端代码与脚本卡片
- `alert_callout` & `change_diff_card`: 变动插播与差分对比卡片
- `sparkline_chart`: 24小时金融分时平滑走势曲线
- `two_column` & `image`: 左右双栏图文绕排与书封展示

