# 2026-09-04 墨水屏全网热榜拓展、防误判灾害预警、MindReset Studio 规范与统一管理界面实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 拓展实用模式与好看样式（网易云热歌榜、豆瓣电影热榜、微信热榜、抖音热榜）、优化灾害预警地区配置防误判、接入MindReset Studio规范模块化，并将设备管理页面重构为与无设备预览页统一的高信息密度卡片与固定预览布局风格。

**Architecture:**
1. 后端：拓展 `HotlistService` 支持 `netease`（网易云）、`douban`（豆瓣电影）、`wechat`（微信）、`douyin`（抖音）抓取与兜底；
2. 渲染器：升级 `hotlist_board` 预设，为音乐曲目、电影星级、社交热搜绘制特色指示标与优雅排版；
3. 灾害预警：增强 `check_device_disaster_alert`，支持城市白名单与地理距离围栏（<= 120km），并在设备配置中支持配置 `disaster_alert` 地区与开关；
4. 前端：重构 `webapp/app/config/page.tsx`，采纳与 `webapp/app/preview/page.tsx` 统一的高信息密度两栏（左侧模块卡片库/模式循环池，右侧固定墨水屏实时画布与设备快捷操作）设计；更新 MindReset Studio 模块定义。

---

### Task 1: 拓展 HotlistService 支持网易云、豆瓣、微信与抖音热榜

**Files:**
- Modify: `backend/core/hotlist_service.py`
- Modify: `backend/core/modes/builtin/hotlist.json` & `backend/core/modes/builtin/en/hotlist.json`
- Test: `backend/tests/test_hotlist_extensions.py`

- [ ] **Step 1: 编写测试用例**
- [ ] **Step 2: 运行测试并验证其针对新平台行为**
- [ ] **Step 3: 实现平台解析、抓取与兜底数据**
- [ ] **Step 4: 测试全部通过**

---

### Task 2: 增强灾害预警精准地区过滤与防误判逻辑

**Files:**
- Modify: `backend/core/disaster_service.py`
- Modify: `backend/core/modes/builtin/disaster_alert.json`
- Test: `backend/tests/test_disaster_region_filter.py`

- [ ] **Step 1: 编写地区匹配与防误判测试**
- [ ] **Step 2: 实现距离计算、省市文本重合判断与跨区过滤**
- [ ] **Step 3: 运行验证测试通过**

---

### Task 3: 建立 MindReset Studio 模块化规范与元信息

**Files:**
- Create: `backend/core/studio_modules.py`
- Modify: `backend/core/mode_registry.py`
- Test: `backend/tests/test_studio_modules.py`

- [ ] **Step 1: 规范化输出各模式的 Studio 分类与能力标签**
- [ ] **Step 2: 验证 API `/api/modes` 输出符合规范**

---

### Task 4: 重构 Web 设备管理页面，与无设备预览页视觉与布局统一

**Files:**
- Modify: `webapp/app/config/page.tsx`
- Modify: `webapp/components/config/eink-preview-panel.tsx`
- Modify: `webapp/components/preview/configs/hotlist-config.tsx`
- Modify: `webapp/components/preview/configs/disaster-config.tsx`

- [ ] **Step 1: 引入左侧高信息密度模块卡片栏（生活、效率、资讯、Studio），与右侧固定预览画布结合**
- [ ] **Step 2: 在设备管理与弹窗中支持灾害预警的城市地区设置**
- [ ] **Step 3: 执行 Next.js 构建验证**

---

### Task 5: 端到端验证与服务重启

- [ ] **Step 1: 运行所有相关自动化测试**
- [ ] **Step 2: 启动验证线上渲染接口**
- [ ] **Step 3: 提交代码并核验**
