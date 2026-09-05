# Git 分支说明与协作流规范 (Branch Strategy)

为了保障 InkSight 软硬件系统、云端后端与 WebApp 前端的长期稳定性与高频率自主演进，项目严格执行清晰规范的 Git 分支流策略。

---

## 一、当前核心分支

- **生产主分支：`main`**
  - 当前在线服务（包括前端管理面板、文档中心 `https://kellson.dpdns.org:3001/zh/docs` 以及后端 REST/Device API）直接追踪并运行在 **`main` 分支**；
  - 远端仓库权威地址：`git@github.com:kellyson520/inksight.git`；
  - 所有的提交必须保证能够通过自动化测试套件（`pytest`）以及 Next.js 静态编译（`npm run build`）。

---

## 二、分支职责与生命周期

```text
       feat/fix/refactor branch
               ↓
    [本地验证 + 测试通过]
               ↓
           main 分支 (权威发布分支)
               ↓
  [自动化构建 + 重启生产服务自愈]
```

1. **功能与修复提交（Atomic Commits）**：
   - 遵循业界 Conventional Commits 语义化前缀：
     - `feat(...)`: 新功能、新增模式、新增排版 Block；
     - `fix(...)`: Bug 修复、降级容灾、排版尺寸对齐修复；
     - `perf(...)`: 性能提升、向量化运算加速、Pillow LUT 优化；
     - `docs(...)`: 文档扩充、操作手册、分支与更新日志维护。
2. **零容忍回归（Zero-Regression Gate）**：
   - 任何改动合并进 `main` 之前，必须在本地完整运行测试矩阵；
   - 生产环境中执行 `systemctl restart inksight-backend inksight-web` 后必须确认状态为 `active`。

---

## 三、部署与更新说明

当需要同步远端最新演进时：
```bash
# 1. 检出权威主分支
git checkout main

# 2. 拉取最新提交
git pull origin main

# 3. 依赖与字体确认
cd backend && pip install -r requirements.txt
python scripts/setup_fonts.py

# 4. WebApp 构建
cd ../webapp && npm install && npm run build

# 5. 重启守护进程
sudo systemctl restart inksight-backend inksight-web
```
