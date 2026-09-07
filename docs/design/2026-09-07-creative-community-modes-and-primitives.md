# 创意社区模式与底层排版原语设计 (Creative Community Modes & Primitives)

## 目标
网罗 GitHub、TRMNL、Tidbyt、InkyPi 等开源极客社区中最受欢迎、最具创意与高粘性的桌面微组件，并迭代 InkSight 底层渲染与数据抓取原语，使墨水屏不仅是日常伴侣，更是极客桌面、科学探索与幽默生活的多彩画布。

## 核心功能规划

### 1. GitHub 开发者脉搏 (GitHub Pulse)
- **核心组件**：`contrib_matrix`（7 行 × 16~20 周的 GitHub Commit 贡献热力图矩阵）。
- **1-bit 墨水屏专研色阶**：
  - Level 0: 细线空心方块
  - Level 1: 中心单点像素
  - Level 2: 50% 棋盘交错网点 (Checkerboard Dithering)
  - Level 3: 实心纯黑填充
- **指标展示**：Streak 连续天数、年度提交总数、今日提交、活跃仓库与主要语言。
- **底层支撑**：`core/github_service.py`，支持公共贡献日历抓取与 Token 查询，内置降级容灾。

### 2. XKCD 每日极客漫画 (XKCD Geek Comic)
- **核心体验**：每日抓取 XKCD 极客与科学幽默四格/单幅漫画。
- **图像优化**：基于 Floyd-Steinberg 误差扩散抖动，将灰度/彩色漫画转化为高对比度 1-bit 纯黑白图像，自适应等比例缩放居中，并在底部保留漫画标题与经典的隐藏 Alt-Text 俏皮注释。
- **底层支撑**：`core/xkcd_service.py`，结合 `OutboundHttp` 与 `MediaFetcher`。

### 3. 元素周期表·每日一素 (Periodic Element of the Day)
- **核心体验**：每天认识一个化学元素。
- **排版结构**：巨大元素符号方块（包含原子序数、相对原子质量、电子排布式）、所属族类胶囊标签、发现者/年代、以及通俗有趣的自然界存在形式与硬核科学应用。
- **底层支撑**：`core/periodic_table.py`，内置完整标准元素库与每日轮播计算器。

## 底层构建迭代 (Engine Primitives)
1. **排版原语 `contrib_matrix`**：加入 `backend/core/blocks/geek_widgets.py`，支持任意 2D 强度矩阵、自动缩放对齐与月份/星期刻度。
2. **模式定义与注册**：在 `backend/core/modes/builtin/` 增加：
   - `github_pulse.json`
   - `xkcd_comic.json`
   - `element_day.json`
3. **模式分类与多语言**：更新 `backend/core/mode_catalog.py`。

## 验收标准
1. `test_contrib_matrix_block` 单元测试通过，精准生成 7×N 热力矩阵。
2. `test_github_service`、`test_xkcd_service`、`test_periodic_table` 单元测试通过。
3. 真实渲染管道能成功输出 `github_pulse`、`xkcd_comic`、`element_day` 的 PNG 图像，无崩溃无乱码。
4. 全量回归测试通过，Next.js 与 Docker 构建健康。
