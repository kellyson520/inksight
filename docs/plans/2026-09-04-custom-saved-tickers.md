# Custom Saved Tickers (Stocks & Crypto) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 支持用户保存自定义/常看的全球股票代码与加密货币代号至自选列表，支持一键调用、添加、删除与设为默认，方便下次无缝使用。

**Architecture:**
1. 在 `webapp/components/preview/types.ts` 定义常用资产接口 `SavedTicker` 与本地存储键 `INKSIGHT_SAVED_TICKERS` 和 `INKSIGHT_DEFAULT_TICKER`。
2. 在 `mode-config-modal.tsx` 资产配置弹窗中新增【我的常用 / 自选标的】专属管理区域：
   - 显示已保存的代码卡片，支持一键点击填入/预览；
   - 支持对当前输入的代码点击【+ 添加到自选】；
   - 支持代码右上角【✕ 移除】自选；
   - 支持【设为默认】，下次进入资产行情自动载入该标的。
3. 在 `preview/page.tsx` 中与 `localStorage` 同步，初次载入自动恢复用户保存的默认标的，切换时自动保存偏好。

**Tech Stack:** React 19, Next.js 16, TypeScript, Tailwind CSS v4, Lucide Icons, FastAPI backend.

---

### Task 1: 定义自选资产类型与存储工具

**Files:**
- Modify: `webapp/components/preview/types.ts`

- [ ] **Step 1:** 添加 `SavedTicker` 结构与 `DEFAULT_SAVED_TICKERS` 初始列表。
- [ ] **Step 2:** 添加本地存储辅助函数 `loadSavedTickers` 和 `saveCustomTickers`。

---

### Task 2: 在 ModeConfigModal 中集成自选标的保存与管理组件

**Files:**
- Modify: `webapp/components/preview/mode-config-modal.tsx`

- [ ] **Step 1:** 在 `ModeConfigModal` 中引入自选资产状态与本地存储同步。
- [ ] **Step 2:** 在输入框旁边提供【保存到自选】按钮；已存在时显示【已保存 / 设为默认】。
- [ ] **Step 3:** 渲染【我的自选标的】栏目，展示徽章标签，支持点击直接应用、点击 ✕ 移除。

---

### Task 3: 在 preview/page.tsx 中打通初次加载与默认标的持久化

**Files:**
- Modify: `webapp/app/preview/page.tsx`

- [ ] **Step 1:** 组件挂载时从 `localStorage` 读取用户自定义的默认 ticker（若有），初始化 `cryptoSymbol`。
- [ ] **Step 2:** 用户在弹窗中选择或保存标的时，自动同步至 `localStorage`。

---

### Task 4: 端到端验证与测试

- [ ] **Step 1:** 运行 Next.js build 验证 TypeScript 编译无误。
- [ ] **Step 2:** 验证后端渲染接口支持所添加的自选股票与加密货币。
- [ ] **Step 3:** 提交并推送至 git 仓库。
