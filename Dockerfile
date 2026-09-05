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
    INKSIGHT_BACKEND_API_BASE="http://127.0.0.1:8070"

# 1. 切换镜像源并安装基础系统依赖与 supervisor 守护进程
RUN if [ -f /etc/apt/sources.list.d/debian.sources ]; then \
        sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources; \
    else \
        sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list; \
    fi \
    && apt-get update && apt-get install -y --no-install-recommends \
        curl \
        ca-certificates \
        supervisor \
        libfreetype6 \
        libjpeg-dev \
        tzdata \
    && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone \
    && rm -rf /var/lib/apt/lists/*

# 2. 从官方 Node.js 镜像直接拷贝已就绪的 Node 与 npm 运行时
COPY --from=node:20-slim /usr/local/lib/node_modules /usr/local/lib/node_modules
COPY --from=node:20-slim /usr/local/bin /usr/local/bin

# 3. 安装 Python 依赖
COPY backend/requirements.txt /app/backend/
RUN pip install --no-cache-dir -i https://mirrors.aliyun.com/pypi/simple/ --upgrade pip && \
    pip install --no-cache-dir -i https://mirrors.aliyun.com/pypi/simple/ -r /app/backend/requirements.txt

# 4. 复制后端源码、文档与预置字体
COPY backend/ /app/backend/
COPY docs/ /app/docs/
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

# 7. 创建持久化数据与日志目录
RUN mkdir -p /app/backend/data /app/backend/logs /var/log/supervisor /app/backend/runtime_uploads

WORKDIR /app

# 暴露端口: 3000 (Web 前端及 API 聚合), 8070 (后端直连端口)
EXPOSE 3000 8070

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:3000/ || exit 1

ENTRYPOINT ["/app/entrypoint.sh"]
