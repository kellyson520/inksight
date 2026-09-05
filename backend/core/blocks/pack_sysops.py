"""
InkSight 扩充排版组件库 2：极客控制台与系统运维组件 (SysOps & Geek Widgets)
包含：
16. terminal_header: 终端控制台三色状态顶栏
17. memory_usage_pill: 内存/缓存分段占用胶囊
18. port_status_badge: 服务与端口监听状态胶囊
19. docker_container_card: 容器状态卡片
20. network_speed_duo: 网络上下行速率双向对流
21. git_commit_row: Git 提交哈希与分支行
22. env_variable_badge: 环境变量/配置徽章
23. log_stream_line: 紧凑日志流水行
24. disk_partition_gauge: 磁盘挂载点分区量规
25. cpu_core_matrix: 多核 CPU 负载小方块阵列
26. ping_latency_chip: 网络 Ping 延迟微胶囊
27. uptime_counter: 系统连续运行时间时钟
28. thread_pool_dots: 线程/进程池状态点阵
29. service_health_pill: 守护进程存活探针胶囊
30. database_qps_metric: 数据库读写 QPS/TPS 指标块
【规范约束】：严格禁止 Emoji。
"""
from __future__ import annotations

import logging
from typing import Any
from PIL import ImageDraw

from core.patterns.utils import (
    EINK_BG,
    EINK_FG,
    EINK_COLOR_NAME_MAP,
    load_font,
    safe_font_bbox,
)
from .context import RenderContext
from .registry import register_block

logger = logging.getLogger(__name__)

_RED = EINK_COLOR_NAME_MAP.get("red", 3 if 3 in EINK_COLOR_NAME_MAP.values() else 2)


def _draw_box(draw: ImageDraw.ImageDraw, bbox: tuple[int, int, int, int], outline=EINK_FG, fill=None, width=1):
    draw.rectangle(bbox, outline=outline, fill=fill, width=width)


@register_block("terminal_header")
def render_terminal_header(ctx: RenderContext, block: dict) -> None:
    """渲染终端三圆点顶栏。"""
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 6) * ctx.scale)
    title = str(block.get("title") or "bash - inksight@node-01")
    w = ctx.available_width - margin_x * 2
    x = ctx.x_offset + margin_x
    y = ctx.y
    h = 16

    _draw_box(ctx.draw, (x, y, x + w, y + h), outline=EINK_FG, fill=EINK_FG)
    # 3 dots
    for i in range(3):
        ctx.draw.ellipse((x + 6 + i * 7, y + 4, x + 6 + i * 7 + 4, y + 8), fill=EINK_BG)
    font = load_font("noto_serif_regular", int(8 * ctx.scale))
    ctx.draw.text((x + 32, y + 2), title, fill=EINK_BG, font=font)
    ctx.y = y + h + margin_bottom


@register_block("memory_usage_pill")
def render_memory_usage_pill(ctx: RenderContext, block: dict) -> None:
    """内存/缓存分段占用胶囊。"""
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 6) * ctx.scale)
    used_gb = float(block.get("used_gb", 12.4))
    total_gb = float(block.get("total_gb", 16.0))
    x = ctx.x_offset + margin_x
    y = ctx.y
    w = ctx.available_width - margin_x * 2

    font = load_font("noto_serif_regular", int(9 * ctx.scale))
    ctx.draw.text((x, y), f"MEM: {used_gb:.1f}G / {total_gb:.1f}G", fill=EINK_FG, font=font)
    by = y + 13
    _draw_box(ctx.draw, (x, by, x + w, by + 6), outline=EINK_FG, width=1)
    fill_w = int(w * (used_gb / total_gb))
    if fill_w > 0:
        _draw_box(ctx.draw, (x, by, x + fill_w, by + 6), fill=EINK_FG)
    ctx.y = by + 8 + margin_bottom


@register_block("port_status_badge")
def render_port_status_badge(ctx: RenderContext, block: dict) -> None:
    """端口与服务监听徽章。"""
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 4) * ctx.scale)
    port = str(block.get("port", "8080"))
    service = str(block.get("service", "uvicorn"))
    x = ctx.x_offset + margin_x
    y = ctx.y

    font = load_font("noto_serif_regular", int(9 * ctx.scale))
    text = f":{port} [{service}] LISTEN"
    tb = safe_font_bbox(font, text)
    bw = (tb[2] - tb[0]) + 10
    _draw_box(ctx.draw, (x, y, x + bw, y + 14), outline=EINK_FG, width=1)
    ctx.draw.text((x + 5, y + 1), text, fill=EINK_FG, font=font)
    ctx.y = y + 16 + margin_bottom


@register_block("docker_container_card")
def render_docker_container_card(ctx: RenderContext, block: dict) -> None:
    """Docker 容器状态卡片。"""
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 6) * ctx.scale)
    name = str(block.get("name", "inksight-api"))
    image = str(block.get("image", "python:3.10-slim"))
    uptime = str(block.get("uptime", "Up 14 days"))
    x = ctx.x_offset + margin_x
    y = ctx.y
    w = ctx.available_width - margin_x * 2

    _draw_box(ctx.draw, (x, y, x + w, y + 26), outline=EINK_FG, width=1)
    font_b = load_font("noto_serif_bold", int(9 * ctx.scale))
    font_r = load_font("noto_serif_regular", int(8 * ctx.scale))
    ctx.draw.text((x + 6, y + 3), f"[CONTAINER] {name}", fill=EINK_FG, font=font_b)
    ctx.draw.text((x + 6, y + 14), f"{image} · {uptime}", fill=EINK_FG, font=font_r)
    ctx.y = y + 28 + margin_bottom


@register_block("network_speed_duo")
def render_network_speed_duo(ctx: RenderContext, block: dict) -> None:
    """网络双向上下行速率。"""
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 6) * ctx.scale)
    up = str(block.get("up", "1.2 MB/s"))
    down = str(block.get("down", "8.5 MB/s"))
    x = ctx.x_offset + margin_x
    y = ctx.y

    font = load_font("noto_serif_bold", int(10 * ctx.scale))
    text = f"UP: {up}  |  DOWN: {down}"
    ctx.draw.text((x, y), text, fill=EINK_FG, font=font)
    ctx.y = y + 14 + margin_bottom


@register_block("git_commit_row")
def render_git_commit_row(ctx: RenderContext, block: dict) -> None:
    """Git Commit 简报行。"""
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 4) * ctx.scale)
    sha = str(block.get("sha", "3a20d7d"))
    msg = str(block.get("msg", "feat: expand system blocks"))
    x = ctx.x_offset + margin_x
    y = ctx.y

    font_b = load_font("noto_serif_bold", int(9 * ctx.scale))
    font_r = load_font("noto_serif_regular", int(9 * ctx.scale))
    _draw_box(ctx.draw, (x, y, x + 44, y + 13), fill=EINK_FG)
    ctx.draw.text((x + 3, y + 1), sha, fill=EINK_BG, font=font_b)
    ctx.draw.text((x + 50, y + 1), msg, fill=EINK_FG, font=font_r)
    ctx.y = y + 16 + margin_bottom


@register_block("env_variable_badge")
def render_env_variable_badge(ctx: RenderContext, block: dict) -> None:
    """环境变量小徽章。"""
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 4) * ctx.scale)
    k = str(block.get("key", "NODE_ENV"))
    v = str(block.get("val", "production"))
    x = ctx.x_offset + margin_x
    y = ctx.y

    font = load_font("noto_serif_regular", int(9 * ctx.scale))
    text = f"{k}={v}"
    tb = safe_font_bbox(font, text)
    bw = (tb[2] - tb[0]) + 8
    _draw_box(ctx.draw, (x, y, x + bw, y + 13), outline=EINK_FG, width=1)
    ctx.draw.text((x + 4, y + 1), text, fill=EINK_FG, font=font)
    ctx.y = y + 15 + margin_bottom


@register_block("log_stream_line")
def render_log_stream_line(ctx: RenderContext, block: dict) -> None:
    """单行日志流。"""
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 3) * ctx.scale)
    level = str(block.get("level", "INFO"))
    msg = str(block.get("msg", "HTTP 200 OK /api/render 28ms"))
    x = ctx.x_offset + margin_x
    y = ctx.y

    font = load_font("noto_serif_regular", int(8 * ctx.scale))
    text = f"[{level}] {msg}"
    ctx.draw.text((x, y), text, fill=EINK_FG, font=font)
    ctx.y = y + 11 + margin_bottom


@register_block("disk_partition_gauge")
def render_disk_partition_gauge(ctx: RenderContext, block: dict) -> None:
    """磁盘挂载点分区量规。"""
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 6) * ctx.scale)
    mount = str(block.get("mount", "/data"))
    pct = float(block.get("pct", 58.0))
    x = ctx.x_offset + margin_x
    y = ctx.y
    w = ctx.available_width - margin_x * 2

    font = load_font("noto_serif_regular", int(9 * ctx.scale))
    ctx.draw.text((x, y), f"{mount} ({pct:.0f}% used)", fill=EINK_FG, font=font)
    by = y + 12
    _draw_box(ctx.draw, (x, by, x + w, by + 5), outline=EINK_FG, width=1)
    fw = int(w * (pct / 100.0))
    if fw > 0:
        _draw_box(ctx.draw, (x, by, x + fw, by + 5), fill=EINK_FG)
    ctx.y = by + 7 + margin_bottom


@register_block("cpu_core_matrix")
def render_cpu_core_matrix(ctx: RenderContext, block: dict) -> None:
    """多核 CPU 负载方块点阵 (8核/16核)。"""
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 6) * ctx.scale)
    loads = block.get("loads") or [20, 85, 45, 90, 30, 60, 15, 70]
    x = ctx.x_offset + margin_x
    y = ctx.y

    font = load_font("noto_serif_regular", int(8 * ctx.scale))
    ctx.draw.text((x, y), "CPU CORES:", fill=EINK_FG, font=font)
    sx = x + 60
    for i, ld in enumerate(loads):
        bx = sx + i * 11
        fill = EINK_FG if ld > 50 else None
        _draw_box(ctx.draw, (bx, y + 1, bx + 8, y + 9), outline=EINK_FG, fill=fill)
    ctx.y = y + 12 + margin_bottom


@register_block("ping_latency_chip")
def render_ping_latency_chip(ctx: RenderContext, block: dict) -> None:
    """网络 Ping 延迟芯片徽章。"""
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 4) * ctx.scale)
    host = str(block.get("host", "1.1.1.1"))
    ms = str(block.get("ms", "14ms"))
    x = ctx.x_offset + margin_x
    y = ctx.y

    font = load_font("noto_serif_regular", int(9 * ctx.scale))
    text = f"PING {host}: {ms}"
    tb = safe_font_bbox(font, text)
    bw = (tb[2] - tb[0]) + 8
    _draw_box(ctx.draw, (x, y, x + bw, y + 13), outline=EINK_FG, width=1)
    ctx.draw.text((x + 4, y + 1), text, fill=EINK_FG, font=font)
    ctx.y = y + 15 + margin_bottom


@register_block("uptime_counter")
def render_uptime_counter(ctx: RenderContext, block: dict) -> None:
    """系统连续运行时间指示行。"""
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 4) * ctx.scale)
    uptime_str = str(block.get("uptime", "42d 18h 32m"))
    x = ctx.x_offset + margin_x
    y = ctx.y

    font = load_font("noto_serif_bold", int(10 * ctx.scale))
    ctx.draw.text((x, y), f"UPTIME: {uptime_str}", fill=EINK_FG, font=font)
    ctx.y = y + 13 + margin_bottom


@register_block("thread_pool_dots")
def render_thread_pool_dots(ctx: RenderContext, block: dict) -> None:
    """线程池状态圆点。"""
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 4) * ctx.scale)
    active = int(block.get("active", 6))
    total = int(block.get("total", 8))
    x = ctx.x_offset + margin_x
    y = ctx.y

    font = load_font("noto_serif_regular", int(8 * ctx.scale))
    ctx.draw.text((x, y), "THREADS:", fill=EINK_FG, font=font)
    sx = x + 50
    for i in range(total):
        dx = sx + i * 8
        fill = EINK_FG if i < active else None
        ctx.draw.ellipse((dx, y + 2, dx + 5, y + 7), outline=EINK_FG, fill=fill)
    ctx.y = y + 11 + margin_bottom


@register_block("service_health_pill")
def render_service_health_pill(ctx: RenderContext, block: dict) -> None:
    """服务健康探针胶囊。"""
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 4) * ctx.scale)
    svc = str(block.get("service", "nginx"))
    status = str(block.get("status", "HEALTHY"))
    x = ctx.x_offset + margin_x
    y = ctx.y

    font = load_font("noto_serif_regular", int(8 * ctx.scale))
    text = f"{svc}: {status}"
    tb = safe_font_bbox(font, text)
    bw = (tb[2] - tb[0]) + 10
    _draw_box(ctx.draw, (x, y, x + bw, y + 12), fill=EINK_FG)
    ctx.draw.text((x + 5, y + 1), text, fill=EINK_BG, font=font)
    ctx.y = y + 14 + margin_bottom


@register_block("database_qps_metric")
def render_database_qps_metric(ctx: RenderContext, block: dict) -> None:
    """数据库 QPS/TPS 指标块。"""
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 6) * ctx.scale)
    qps = str(block.get("qps", "3,420"))
    tps = str(block.get("tps", "410"))
    x = ctx.x_offset + margin_x
    y = ctx.y

    font_b = load_font("noto_serif_bold", int(10 * ctx.scale))
    font_r = load_font("noto_serif_regular", int(8 * ctx.scale))
    ctx.draw.text((x, y), f"DB QPS: {qps}", fill=EINK_FG, font=font_b)
    ctx.draw.text((x + 100, y + 1), f"(TPS: {tps})", fill=EINK_FG, font=font_r)
    ctx.y = y + 14 + margin_bottom
