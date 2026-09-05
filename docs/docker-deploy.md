# InkSight Docker 一键部署指南 (单容器 All-in-One)

InkSight 提供工业级**单容器（All-in-One）**极简部署模式。在一个轻量容器内同时集成 Python FastAPI 图像与数据渲染后端、Next.js Web 管理控制台与 Supervisor 进程自愈守护。

无论是个人家用 NAS、群晖 Synology、威联通 QNAP、树莓派还是云服务器，仅需一行命令即可完成整套智能墨水屏系统的上线。

---

## 一、极简启动 (一行命令)

### 方式 1：使用 Docker Run 直接运行
```bash
# 创建本地持久化数据目录
mkdir -p ./data ./logs

# 启动单容器 (映射 3000 端口)
docker run -d \
  --name inksight \
  --restart unless-stopped \
  -p 3000:3000 \
  -v $(pwd)/data:/app/backend/data \
  -v $(pwd)/logs:/app/backend/logs \
  -e TZ=Asia/Shanghai \
  -e DEEPSEEK_API_KEY="你的DeepSeek_Key" \
  kellyson520/inksight:latest
```

启动完成后，打开浏览器访问：
- **Web 管理控制台与模式广场**：`http://服务器IP:3000`
- **墨水屏设备端拉取接口**：`http://服务器IP:3000/api/render?mac=你的设备MAC`

---

### 方式 2：使用 Docker Compose 一键启动 (推荐)

项目根目录已内置生产级 `docker-compose.yml`。

#### 1. 克隆代码与配置环境变量
```bash
git clone https://github.com/kellyson520/inksight.git
cd inksight

# 复制环境变量模板
cp .env.docker.example .env

# 编辑填入你的 API Key (如 DeepSeek、百炼等)
vim .env
```

#### 2. 一键启动
```bash
docker compose up -d
```

#### 3. 查看运行日志与状态
```bash
docker compose logs -f
```

---

## 二、架构优势与特性

1. **单容器全栈整合**：
   - 内部已做好前端对后端的自动反向代理，向外仅需暴露 `3000` 端口即可享受网页管理 + 墨水屏设备通信；
   - 告别多容器跨 Bridge 网络通信失败或跨域配置繁琐的痛点。
2. **数据持久化与升级无损**：
   - 所有设备配置、历史渲染缓存、个性化语录数据库均安全保存在宿主机挂载的 `./data` 目录中；
   - 后续升级镜像只需 `docker compose pull && docker compose up -d`，历史数据与设备配置零丢失。
3. **Supervisor 进程守护自愈**：
   - 容器内嵌 Supervisor 进程管理器，监测并保障前端与后端持续存活，发生异常自动在秒级重新拉起。
4. **字库全量内置**：
   - 镜像构建阶段已内置 Google Noto Serif 衬线中英文字库，中西文、音标字符显示锐利典雅。

---

## 三、常用运维命令

```bash
# 查看容器状态与健康检查
docker ps -f name=inksight

# 重启服务
docker compose restart

# 更新至最新镜像
docker compose pull
docker compose up -d

# 进入容器调试
docker exec -it inksight bash
```
