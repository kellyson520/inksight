#!/bin/bash
set -e

echo "[InkSight] Starting All-in-One Container..."

# 确保数据目录与日志目录存在
mkdir -p /app/backend/data /app/backend/logs /var/log/supervisor

# 确保字体文件就绪
if [ ! -d "/app/backend/fonts/truetype" ] || [ -z "$(ls -A /app/backend/fonts/truetype 2>/dev/null)" ]; then
    echo "[InkSight] Downloading fonts..."
    cd /app/backend && python scripts/setup_fonts.py || true
fi

echo "[InkSight] Launching Backend & Web via Supervisord..."
exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf
