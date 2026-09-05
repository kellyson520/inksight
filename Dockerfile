# ========================================================
# InkSight All-in-One 单容器 Dockerfile (生产多阶段构建)
# 包含：FastAPI 后端 + Next.js Web 控制台 + 进程自愈守护
# ========================================================

# --------------------------------------------------------
# 阶段 1: 编译 Next.js Web 前端
# --------------------------------------------------------
FROM node:20-alpine AS web-builder
WORKDIR /app/webapp
COPY webapp/package.json webapp/package-lock.json* ./
RUN npm ci
COPY webapp/ ./
ENV NEXT_TELEMETRY_DISABLED=1
ENV NODE_ENV=production
RUN npm run build

# --------------------------------------------------------
# 阶段 2: 组装一体化生产运行镜像
# --------------------------------------------------------
FROM python:3.10-slim AS runner

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    INKSIGHT_ENV=production \
    TZ=Asia/Shanghai \
    NEXT_TELEMETRY_DISABLED=1 \
    NODE_ENV=production \
    INKSIGHT_BACKEND_API_BASE="http://127.0.0.1:8080"

# 1. 安装基础依赖、图形字体库、Node.js 20 与 supervisor 守护进程
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    gnupg \
    supervisor \
    libopus0 \
    libopus-dev \
    libfreetype6 \
    libfreetype6-dev \
    libjpeg-dev \
    zlib1g-dev \
    tzdata \
    && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone \
    && mkdir -p /etc/apt/keyrings \
    && curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg \
    && echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_20.x nodistro main" | tee /etc/apt/sources.list.d/nodesource.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

# 2. 安装 Python 依赖
COPY backend/requirements.txt /app/backend/
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /app/backend/requirements.txt

# 3. 复制后端完整源码
COPY backend/ /app/backend/

# 4. 复制预设字体
RUN cd /app/backend && python scripts/setup_fonts.py || true

# 5. 复制前端构建产物及依赖
WORKDIR /app/webapp
COPY --from=web-builder /app/webapp/public ./public
COPY --from=web-builder /app/webapp/.next ./.next
COPY --from=web-builder /app/webapp/node_modules ./node_modules
COPY --from=web-builder /app/webapp/package.json ./package.json
COPY --from=web-builder /app/webapp/messages ./messages

# 6. 配置 supervisord 与启动入口
COPY docker/supervisord.conf /etc/supervisor/conf.d/supervisord.conf
COPY docker/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# 7. 创建持久化目录
RUN mkdir -p /app/backend/data /app/backend/logs /var/log/supervisor

WORKDIR /app

# 暴露端口: 3000 (Web 前端及 API 聚合), 8080 (后端直连调试端口)
EXPOSE 3000 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:3000/ || exit 1

ENTRYPOINT ["/app/entrypoint.sh"]
