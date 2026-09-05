# ==========================================
# InkSight Backend Dockerfile
# Python 3.10 + FastAPI + PIL 图像渲染引擎
# ==========================================
FROM python:3.10-slim AS runner

WORKDIR /app

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    INKSIGHT_ENV=production \
    TZ=Asia/Shanghai

# 安装系统级依赖（字体渲染、C++构建库、网络与音频依赖）
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gcc \
    g++ \
    libopus0 \
    libopus-dev \
    libfreetype6 \
    libfreetype6-dev \
    libjpeg-dev \
    zlib1g-dev \
    tzdata \
    && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖清单并安装 Python 包
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 复制后端源码
COPY . .

# 自动确保字体就绪
RUN python scripts/setup_fonts.py || true

# 创建持久化数据目录
RUN mkdir -p /app/data /app/logs

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

CMD ["python", "-m", "uvicorn", "api.index:app", "--host", "0.0.0.0", "--port", "8080"]
