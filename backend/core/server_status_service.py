"""
InkSight 服务器与主机监控基础设施服务 (Server Status Infrastructure Service)
负责采集当前主机的真实性能指标 (CPU, 内存, 磁盘, 负载, Uptime),
同时接收外部服务器/宝塔面板/NAS 通过 HTTP POST 投递的远程探针数据，
并提供一键配置的 Shell 上报脚本。
"""
from __future__ import annotations

import logging
import os
import socket
import time
from typing import Any, Optional

logger = logging.getLogger(__name__)

# 全局缓存与远程上报数据
_pushed_server_data: dict[str, dict[str, Any]] = {}
_last_cpu_sample: Optional[tuple[float, float]] = None
_last_sample_time: float = 0.0


def _sample_local_cpu() -> float:
    """采集本地 Linux CPU 使用率（通过 /proc/stat 差值采样或负载估算）。"""
    global _last_cpu_sample, _last_sample_time
    try:
        if not os.path.exists("/proc/stat"):
            load1, _, _ = os.getloadavg()
            cpu_count = os.cpu_count() or 1
            return round(min(100.0, (load1 / cpu_count) * 100.0), 1)

        with open("/proc/stat", "r") as f:
            line = f.readline()
            if not line.startswith("cpu"):
                return 0.0
            fields = [float(x) for x in line.strip().split()[1:]]
        idle = fields[3] + (fields[4] if len(fields) > 4 else 0.0)
        total = sum(fields)
        now = time.time()

        if _last_cpu_sample is not None and now - _last_sample_time >= 0.5:
            last_total, last_idle = _last_cpu_sample
            diff_total = total - last_total
            diff_idle = idle - last_idle
            _last_cpu_sample = (total, idle)
            _last_sample_time = now
            if diff_total > 0:
                pct = (1.0 - (diff_idle / diff_total)) * 100.0
                return round(max(0.0, min(100.0, pct)), 1)

        _last_cpu_sample = (total, idle)
        _last_sample_time = now

        load1, _, _ = os.getloadavg()
        cpu_count = os.cpu_count() or 1
        return round(min(100.0, (load1 / cpu_count) * 100.0), 1)
    except Exception as e:
        logger.debug("[ServerStatus] CPU sample error: %s", e)
        return 0.0


def _sample_local_memory() -> tuple[float, str, float, float]:
    """采集本地内存使用 (使用率%, 显示字符串, 已用GB, 总GB)。"""
    mem_total_kb = 0
    mem_avail_kb = 0
    try:
        if os.path.exists("/proc/meminfo"):
            with open("/proc/meminfo", "r") as f:
                for line in f:
                    if line.startswith("MemTotal:"):
                        mem_total_kb = int(line.split()[1])
                    elif line.startswith("MemAvailable:"):
                        mem_avail_kb = int(line.split()[1])
    except Exception as e:
        logger.debug("[ServerStatus] Meminfo read error: %s", e)

    if mem_total_kb <= 0:
        return 0.0, "0G / 0G", 0.0, 0.0

    mem_used_kb = max(0, mem_total_kb - mem_avail_kb)
    mem_pct = round((mem_used_kb / mem_total_kb) * 100.0, 1)
    used_gb = round(mem_used_kb / 1024 / 1024, 1)
    total_gb = round(mem_total_kb / 1024 / 1024, 1)
    return mem_pct, f"{used_gb}G / {total_gb}G", used_gb, total_gb


def _sample_local_disk() -> tuple[float, str, float, float]:
    """采集本地根目录磁盘使用。"""
    try:
        st = os.statvfs("/")
        total_b = st.f_blocks * st.f_frsize
        avail_b = st.f_bavail * st.f_frsize
        used_b = total_b - avail_b
        pct = round((used_b / total_b) * 100.0, 1) if total_b else 0.0
        free_gb = round(avail_b / (1024**3), 1)
        total_gb = round(total_b / (1024**3), 1)
        return pct, f"{free_gb}G 可用 / {total_gb}G", free_gb, total_gb
    except Exception as e:
        logger.debug("[ServerStatus] Disk stat error: %s", e)
        return 0.0, "N/A", 0.0, 0.0


def _sample_local_uptime() -> str:
    """采集本地运行时间。"""
    try:
        if os.path.exists("/proc/uptime"):
            with open("/proc/uptime", "r") as f:
                up_secs = float(f.read().split()[0])
                days = int(up_secs // 86400)
                hours = int((up_secs % 86400) // 3600)
                mins = int((up_secs % 3600) // 60)
                if days > 0:
                    return f"{days}天 {hours}小时"
                return f"{hours}小时 {mins}分"
    except Exception:
        pass
    return "已运行"


class ServerStatusService:
    """服务器性能与探针数据核心服务。"""

    def get_local_metrics(self) -> dict[str, Any]:
        """采集当前宿主机指标。"""
        cpu_pct = _sample_local_cpu()
        mem_pct, mem_str, used_mem, total_mem = _sample_local_memory()
        disk_pct, disk_str, free_disk, total_disk = _sample_local_disk()
        uptime_str = _sample_local_uptime()

        try:
            load1, load5, load15 = os.getloadavg()
            load_str = f"{load1:.2f} / {load5:.2f} / {load15:.2f}"
        except Exception:
            load_str = "0.00 / 0.00 / 0.00"

        hostname = socket.gethostname() or "Linux-Host"
        return {
            "server_name": hostname,
            "ip": "127.0.0.1",
            "cpu_pct": cpu_pct,
            "mem_pct": mem_pct,
            "mem_str": mem_str,
            "disk_pct": disk_pct,
            "disk_str": disk_str,
            "load_str": load_str,
            "uptime": uptime_str,
            "update_time": time.strftime("%H:%M:%S"),
            "source": "local",
        }

    def record_pushed_metrics(self, key: str, data: dict[str, Any]) -> dict[str, Any]:
        """记录外部推送的服务器状态指标。"""
        clean_key = (key or "default").strip().lower()
        now_str = time.strftime("%H:%M:%S")

        cpu_pct = round(float(data.get("cpu_pct") or data.get("cpu") or 0.0), 1)
        mem_pct = round(float(data.get("mem_pct") or data.get("mem") or 0.0), 1)
        disk_pct = round(float(data.get("disk_pct") or data.get("disk") or 0.0), 1)

        record = {
            "server_name": str(data.get("server_name") or data.get("hostname") or clean_key).strip(),
            "ip": str(data.get("ip") or "").strip(),
            "cpu_pct": max(0.0, min(100.0, cpu_pct)),
            "mem_pct": max(0.0, min(100.0, mem_pct)),
            "mem_str": str(data.get("mem_str") or f"{mem_pct}%").strip(),
            "disk_pct": max(0.0, min(100.0, disk_pct)),
            "disk_str": str(data.get("disk_str") or f"{disk_pct}%").strip(),
            "load_str": str(data.get("load_str") or data.get("load") or "0.00 / 0.00 / 0.00").strip(),
            "uptime": str(data.get("uptime") or "在线").strip(),
            "update_time": now_str,
            "source": "pushed",
        }
        _pushed_server_data[clean_key] = record
        logger.info("[ServerStatus] Pushed status updated for '%s': CPU %s%%, MEM %s%%", clean_key, cpu_pct, mem_pct)
        return record

    def get_metrics_for_mode(self, server_key: Optional[str] = None) -> dict[str, Any]:
        """获取用于墨水屏渲染的指标字典（优先使用匹配的远程上报数据，否则回退到宿主机本地）。"""
        if server_key:
            clean = server_key.strip().lower()
            if clean in _pushed_server_data:
                return dict(_pushed_server_data[clean])

        if "default" in _pushed_server_data:
            return dict(_pushed_server_data["default"])

        if _pushed_server_data:
            # 返回最新上报的记录
            first_key = list(_pushed_server_data.keys())[0]
            return dict(_pushed_server_data[first_key])

        return self.get_local_metrics()

    def generate_shell_script(self, report_url: str, server_name: str = "") -> str:
        """生成一键上报探针 Shell 脚本，兼容 Linux/宝塔计划任务/Crontab。"""
        return f"""#!/usr/bin/env bash
# ==============================================================================
# InkSight 墨水屏服务器监控一键上报脚本 (Server Status Agent)
# 可放入 Crontab (如每 2 分钟执行一次) 或宝塔面板计划任务
# ==============================================================================
REPORT_URL="{report_url}"
SERVER_NAME="{server_name}"

if [ -z "$SERVER_NAME" ]; then
    SERVER_NAME=$(hostname)
fi

# 1. 采集 CPU 使用率 (采样 1 秒)
cpu_sample() {{
    read cpu user nice system idle iowait irq softirq steal guest < <(grep '^cpu ' /proc/stat)
    total1=$((user+nice+system+idle+iowait+irq+softirq+steal))
    idle1=$((idle+iowait))
    sleep 1
    read cpu user nice system idle iowait irq softirq steal guest < <(grep '^cpu ' /proc/stat)
    total2=$((user+nice+system+idle+iowait+irq+softirq+steal))
    idle2=$((idle+iowait))
    dt=$((total2-total1))
    di=$((idle2-idle1))
    if [ "$dt" -gt 0 ]; then
        awk -v di="$di" -v dt="$dt" 'BEGIN{{ printf("%.1f", (1-(di/dt))*100) }}'
    else
        echo "0.0"
    fi
}}

# 2. 采集内存信息
mem_info() {{
    total=$(grep -i '^MemTotal:' /proc/meminfo | awk '{{print $2}}')
    avail=$(grep -i '^MemAvailable:' /proc/meminfo | awk '{{print $2}}')
    used=$((total-avail))
    pct=$(awk -v u="$used" -v t="$total" 'BEGIN{{ printf("%.1f", u*100/t) }}')
    usedg=$(awk -v u="$used" 'BEGIN{{ printf("%.1f", u/1024/1024) }}')
    totalg=$(awk -v t="$total" 'BEGIN{{ printf("%.1f", t/1024/1024) }}')
    echo "$pct ${{usedg}}G/${{totalg}}G"
}}

# 3. 采集根分区磁盘信息
disk_info() {{
    df -h / | awk 'NR==2 {{print $5, $4" 可用/"$2}}' | sed 's/%//'
}}

# 4. 采集系统负载与在线时长
load_txt() {{
    awk '{{printf "%s / %s / %s", $1,$2,$3}}' /proc/loadavg
}}

uptime_txt() {{
    awk '{{d=int($1/86400); h=int(($1%86400)/3600); if(d>0) printf "%d天%d时", d, h; else printf "%d时", h}}' /proc/uptime
}}

CPU_PCT=$(cpu_sample)
read MEM_PCT MEM_STR < <(mem_info)
read DISK_PCT DISK_STR < <(disk_info)
LOAD_STR=$(load_txt)
UPTIME_STR=$(uptime_txt)
IP_ADDR=$(hostname -I | awk '{{print $1}}')

JSON_PAYLOAD=$(cat <<EOF
{{
  "server_name": "${{SERVER_NAME}}",
  "ip": "${{IP_ADDR}}",
  "cpu_pct": ${{CPU_PCT:-0}},
  "mem_pct": ${{MEM_PCT:-0}},
  "mem_str": "${{MEM_STR}}",
  "disk_pct": ${{DISK_PCT:-0}},
  "disk_str": "${{DISK_STR}}",
  "load_str": "${{LOAD_STR}}",
  "uptime": "${{UPTIME_STR}}"
}}
EOF
)

curl -s -X POST "${{REPORT_URL}}" \\
     -H "Content-Type: application/json" \\
     -d "$JSON_PAYLOAD" >/dev/null

echo "InkSight Server Status reported: CPU ${{CPU_PCT}}%, MEM ${{MEM_PCT}}% (${{MEM_STR}})"
"""


server_status_service = ServerStatusService()
