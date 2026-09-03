# InkSight RSS 订阅模式与开放数据源扩展架构设计

## 1. 目标
提升 InkSight 的灵活性与开放性玩法：
- 支持 RSS/Atom 订阅源，自动解析标题、正文摘要、发表时间、作者及配图；
- 兼容各种复杂 RSS 源（包括自建 RSSHub、特殊端口、带自签名/过期证书的 HTTPS 源，如 `https://kellson.dpdns.org:81/playno1/av`）；
- 提供多套优雅的墨水屏排版：图文并茂卡片（headline + cover image + summary）、大字极简新闻卡片、多条目列表卡片；
- 在 Web 端预览界面（`/preview`）提供即时配置、实时拉取与渲染仿真；
- 参考 `dot.mindreset.tech`（Quote/0）的开放生态理念，提供开放文本与快讯推送能力（`/api/open/device/{mac}/text` Webhook），无需改动墨水屏硬件即可展示用户自定义业务数据；
- 保持对墨水屏硬件端点（`/api/render`, `/api/screen`）零改动、零破坏。

## 2. 模块规划
1. **`backend/core/rss_parser.py`**：
   - 健壮的 XML/RSS/Atom 解析器；
   - 提取 title, link, description, pubDate, author；
   - HTML 净化与纯文本摘要提取（移除 HTML 标签、保留标点与关键排版）；
   - 配图提取（`<img src="...">`, `<enclosure>`, `<media:content>` 等）；
   - 支持 SSL 自适应（当遇到自签名/特定内网证书时不中断拉取）；
   - 内存级轻量缓存（避免高频重复拉取源站）。

2. **`backend/core/modes/builtin/rss.json` & `backend/core/modes/builtin/en/rss.json`**：
   - 注册 `RSS` 内置模式；
   - `content.type`: `computed`，`provider`: `rss`；
   - `settings_schema`: 支持 `feed_url`、`item_index`（循环展示前 N 条）、`display_style`（图文/纯文）、`font_size` 等；
   - `layout`: 适配 400x300, 296x128, 648x480, 800x480 各屏幕分辨率，支持图文两栏、首图渲染、来源标签。

3. **`backend/core/json_content.py` & `backend/core/mode_catalog.py`**：
   - 在 `_generate_computed_content` 中接入 `provider == "rss"`；
   - 在 `mode_catalog.py` 中将 `RSS` 列入 `core` 或 `more` 列表，提供中英文标签与说明。

4. **开放 API (`backend/api/routes/open.py`)**：
   - 参考 Dot Quote/0 Open API：`POST /api/open/device/{mac}/text`；
   - 允许用户或第三方系统（Home Assistant、iOS 快捷指令、自建服务）推送实时内容；
   - 自动适配为 MEMO 或 OPEN_TEXT 模式下发到设备。

5. **前端 Web 预览控制台 (`webapp/app/preview/page.tsx`)**：
   - 增加 RSS 模式的预览定制弹窗，用户可直接输入 RSS URL（或点选快捷测试源如用户提供的 `https://kellson.dpdns.org:81/playno1/av`）；
   - 支持设置条目序号（第一篇、第二篇……）、是否展示图片；
   - 实时调用后端并在 E-Ink 画布上无缝渲染。
