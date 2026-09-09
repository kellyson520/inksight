# 四类推荐模块与配置分页设计

## 目标
新增起点小说推荐、Pixiv 每日一图、iwara 视频推荐、P 站视频推荐四个内置模式；每个模式支持排行榜式与封面/缩略图卡片式布局；为外站请求提供统一全局代理配置；将中文设备配置页的模式按类别分页展示。

## 背景与约束
- InkSight 的模式由 JSON layout + Python Provider 组成，Provider 通过 `register_provider` 注册。
- 外部网络请求应集中经过 `core/outbound_http.py`，避免各 Provider 私自创建客户端、绕过重试与安全策略。
- 用户要求用户自己填写代理链接；代理凭据不得写入日志。
- 现有 mode ID、设备配置字段、已有模式行为必须保持兼容。
- 用户禁止委托子代理，本任务全部由主代理直接实现。

## 方案
### Provider 与标准内容
每个 Provider 返回统一字段：`title`、`subtitle`、`source`、`cover_url`、`thumbnail_url`、`rank_label`、`published_at`、`detail_url`、`description`。Provider 负责来源解析、字段清洗、fallback；布局只消费标准字段。

四个模式 ID：
- `QIDIAN_NOVEL`：起点小说榜单/推荐
- `PIXIV_DAILY`：Pixiv 每日一图
- `IWARA_VIDEO`：iwara 视频推荐
- `PORN_VIDEO`：P 站（Pornhub）视频推荐

每个模式提供 `layout_style` 设置：`ranking` 与 `cover_card`。`ranking` 使用文本榜单；`cover_card` 使用封面/缩略图与角标，视觉语言复用 `game_giveaway`。

### 全局代理
在用户个人设置中增加 `global_proxy_url` 字段，支持 `http://`, `https://`, `socks5://`, `socks5h://`。代理设置存入现有 user preferences/config store，通过运行时请求上下文传递给 `outbound_http`。未配置时直连。代理 URL 仅保存和使用，不在日志中输出完整凭据。

### 配置页分页
设备配置页的模式选择改为分类分页：核心、资讯/榜单、图片/视频、系统/工具、自定义。分页状态仅在前端维护，提交仍使用原有 `modes` 数组。分类依据后端 catalog 的 `category`，新增模式声明到 `mode_catalog.py`。

## 接口与数据流
1. 配置页加载 `/api/config/{mac}` 与 `/api/modes/catalog`。
2. 用户选择模式及布局设置，沿用 `mode_overrides[MODE_ID]` 保存 `layout_style` 与来源设置。
3. Provider 从 `kwargs.config` 读取当前用户/设备配置，获取全局代理值。
4. Provider 调用 `outbound_http.get_json/get_text`，请求层应用代理。
5. Provider 返回标准内容，JSON renderer 根据 `layout_style` 渲染对应分支。

## 模块划分
- `backend/core/external_proxy.py`：代理 URL 校验、脱敏、httpx proxy 参数构造。
- `backend/core/recommendation_provider.py`：标准推荐数据结构与通用清洗工具。
- `backend/core/providers/qidian_novel_provider.py`
- `backend/core/providers/pixiv_daily_provider.py`
- `backend/core/providers/iwara_video_provider.py`
- `backend/core/providers/porn_video_provider.py`
- `backend/core/modes/builtin/{qidian_novel,pixiv_daily,iwara_video,porn_video}.json` 及英文对等文件。
- `backend/core/mode_catalog.py`：新增四个 catalog 条目。
- `backend/core/outbound_http.py`：代理参数接入。
- `backend/core/config_store.py` / 用户偏好 API：代理持久化。
- `webapp/app/config/page.tsx` / 配置组件：分类分页与全局代理输入。

## 边界
- 不实现登录、收藏、个性化推荐算法或付费内容抓取。
- 不绕过站点验证码、地域限制或访问控制。
- P 站按公开可访问榜单/推荐页面适配；若源站拒绝自动访问，显示 fallback，而不是绕过限制。
- 代理仅用于后端外站请求，不改变设备网络设置。

## 验收标准
- 四个模式均能被 catalog 发现、配置并通过 preview 渲染。
- 每个模式至少有两种布局，布局设置保存后生效。
- Provider 网络失败时返回可渲染 fallback。
- 配置代理后外站请求使用代理；未配置时不改变现有请求。
- 中文配置页按类别分页，模式选择跨页保持，保存后原配置接口兼容。
- 专项测试、Web 类型检查/构建、生产预览均通过。
