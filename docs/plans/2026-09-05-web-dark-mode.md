# Web 全局黑暗模式与文档更新实施计划 (Web Dark Mode & Docs Plan)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 Web 用户界面（Next.js WebApp，线上地址 `https://kellson.dpdns.org:3001`）增加全局暗黑/深色模式（Dark Mode），提供主题切换能力并完成全站各页面与文档排版适配；同步在文档库中新增暗黑模式操作手册、明确 Git 分支规范，并建立详尽的迭代更新日志（CHANGELOG）。

**Architecture:** 
1. 在 `webapp`（Next.js 16 + Tailwind CSS v4）中配置 `@variant dark (&:where(.dark, .dark *));` 原生深色模式支持，并在根布局通过内联脚本实现防闪烁的暗黑主题加载。
2. 抽象并实现 `ThemeProvider` 与 `ThemeToggle` 交互组件，支持三种主题状态：`light`（浅色日间）、`dark`（深色夜间）、`system`（随系统偏好），并通过 `localStorage` 自动持久化。
3. 全局 CSS 变量（`--color-paper`, `--color-ink` 等）与 Tailwind 工具类（`dark:bg-zinc-950`, `dark:text-zinc-100` 等）全面适配 Header、Navigation、Footer、首页、配置页、文档中心（`docs-prose`）等。
4. 在 `docs/` 和 WebApp 的 `/docs` 路由中新增：
   - Git 分支说明与协作流规范文档（`docs/branching.md`）；
   - Web 界面黑暗模式使用操作手册（`docs/dark-mode.md`）；
   - 项目全面版本迭代更新日志（`docs/changelog.md`）。
5. 同步在 `docs/layout.tsx` 与导航栏更新相应入口。

**Tech Stack:** Next.js 16, React 19, Tailwind CSS v4, Lucide React, Markdown.

---

### Task 1: 配置 Tailwind v4 与根布局的防闪烁暗黑模式体系

**Files:**
- Modify: `webapp/app/globals.css`
- Modify: `webapp/app/layout.tsx`
- Create: `webapp/components/theme-provider.tsx`
- Create: `webapp/components/theme-toggle.tsx`

**Interfaces:**
- Produces: `ThemeProvider` Context 提供 `theme`, `setTheme`, `resolvedTheme`
- Produces: `ThemeToggle` 客户端按钮，点击在浅色/深色/跟随系统之间平滑切换

- [ ] **Step 1: 在 `globals.css` 中注入 Tailwind v4 深色选择器与深色根变量**
- [ ] **Step 2: 创建 `theme-provider.tsx` 提供 React Context 与客户端 `localStorage` 监听**
- [ ] **Step 3: 创建 `theme-toggle.tsx` 提供 Sun/Moon 切换组件**
- [ ] **Step 4: 在 `layout.tsx` 注入初始化脚本防止页面初次加载白屏闪烁（Flash of Unstyled Theme）**

---

### Task 2: 全站核心组件与文档排版适配深色样式

**Files:**
- Modify: `webapp/components/navbar.tsx`
- Modify: `webapp/components/footer.tsx`
- Modify: `webapp/app/globals.css` (docs-prose dark styles)
- Modify: `webapp/messages/zh.json` & `webapp/messages/en.json`

- [ ] **Step 1: 在 `navbar.tsx` 桌面端和移动端菜单嵌入 `ThemeToggle`**
- [ ] **Step 2: 为 `navbar.tsx` 和 `footer.tsx` 适配深色背景、边框与毛玻璃效果**
- [ ] **Step 3: 为 `globals.css` 中的 `.docs-prose`、代码块（`code`/`pre`）、引用块（`blockquote`）与提示框（`.callout`）适配深色高对比度排版**
- [ ] **Step 4: 在多语言字典 `messages/zh.json` 与 `messages/en.json` 补充主题切换多语言标签**

---

### Task 3: 编写操作手册、Git 分支规范与版本迭代更新日志

**Files:**
- Create: `docs/dark-mode.md` (Web 界面暗黑模式操作手册)
- Create: `docs/branching.md` (分支规范与持续集成发布流)
- Create: `docs/changelog.md` (InkSight 详尽迭代日志，从初始版本到 520+ 组件、微信读书与暗黑模式)
- Modify: `webapp/app/docs/layout.tsx` (侧边栏增添分支、暗黑模式与更新日志入口)
- Modify: `webapp/messages/zh.json` & `webapp/messages/en.json` (对应导航项多语言)

- [ ] **Step 1: 编写 `docs/dark-mode.md`，图文说明 Web 界面如何一键切换日/夜间及系统自适应**
- [ ] **Step 2: 编写 `docs/branching.md`，明确当前分支 `main`、开发流程与发布规范**
- [ ] **Step 3: 编写 `docs/changelog.md`，汇总所有功能迭代历程与 Git 提交里程碑**
- [ ] **Step 4: 在 `webapp/app/docs/layout.tsx` 注册新文档页面**

---

### Task 4: WebApp 构建验证、端到端测试与服务发布

**Files:**
- Verify: `npm run build` in `webapp`
- Verify: 服务 `systemctl restart inksight-web`
- Verify: 本地与在线网址 `https://kellson.dpdns.org:3001/zh/docs` 访问正常
- Push: `git add -A && git commit && git push origin main`

- [ ] **Step 1: 在 `webapp` 目录执行 `npm run build` 确保无 TypeScript 或 CSS 构建报错**
- [ ] **Step 2: 重启 `inksight-web` 并检查 HTTP 状态**
- [ ] **Step 3: 提交并推送到远端仓库**
