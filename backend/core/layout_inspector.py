"""
InkSight 墨水屏布局空间反思与语义会话引擎 (AI-Readable Layout Inspector & Session)
将复杂的墨水屏像素排版度量转化为 AI 大模型可直接读懂的结构化会话与 ASCII 版面拓扑，
在自动化输出阶段协助大模型实时察觉视觉截断、留白失衡与字符密度偏差。
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, List, Optional
from PIL import Image, ImageDraw

from core.config import SCREEN_WIDTH, SCREEN_HEIGHT
from core.patterns.utils import EINK_BG, apply_text_fontmode, has_cjk, load_font, wrap_text
from core.blocks.context import RenderContext
from core.blocks.measure import measure_block_size
from core.blocks.text import pick_cjk_font
from core.blocks.spec import BlockSpec
from core.component_tree_engine import (
    _uses_component_tree,
    _build_component_node,
    _measure_component_node,
    _layout_component_node,
    _component_tree_scale,
)
from core.json_renderer import expand_layout_presets, _merge_layout_dict

logger = logging.getLogger(__name__)


@dataclass
class BlockInspection:
    """单个区块的物理排版空间诊断信息。"""
    block_type: str
    x: int
    y: int
    width: int
    height: int
    text_preview: str = ""
    rendered_lines: list[str] = field(default_factory=list)
    is_truncated: bool = False
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class LayoutSession:
    """整块墨水屏物理版面的全局语义会话。"""
    mode_id: str
    screen_w: int
    screen_h: int
    status_bar_h: int
    footer_h: int
    footer_top: int
    available_body_height: int
    body_height_used: int
    remaining_height_px: int
    fill_ratio: float
    density_assessment: str  # "sparse" | "balanced" | "crowded"
    has_truncation: bool
    warnings: list[str] = field(default_factory=list)
    blocks: list[BlockInspection] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode_id": self.mode_id,
            "screen": f"{self.screen_w}x{self.screen_h}",
            "status_bar_height": self.status_bar_h,
            "footer_height": self.footer_h,
            "footer_top": self.footer_top,
            "available_body_height": self.available_body_height,
            "body_height_used": self.body_height_used,
            "remaining_height_px": self.remaining_height_px,
            "fill_ratio_percent": round(self.fill_ratio * 100, 1),
            "density_assessment": self.density_assessment,
            "has_truncation": self.has_truncation,
            "warnings": self.warnings,
            "blocks_count": len(self.blocks),
            "blocks": [
                {
                    "type": b.block_type,
                    "rect": [b.x, b.y, b.width, b.height],
                    "lines_count": len(b.rendered_lines),
                    "text_preview": b.text_preview[:60],
                    "is_truncated": b.is_truncated,
                }
                for b in self.blocks
            ],
        }


def inspect_layout(
    mode_def: dict,
    content: dict,
    screen_w: int = SCREEN_WIDTH,
    screen_h: int = SCREEN_HEIGHT,
    colors: int = 2,
    language: str = "zh",
) -> LayoutSession:
    """虚拟排版测量，提取墨水屏版面的空间分布与诊断数据。"""
    mode_id = mode_def.get("mode_id", "UNKNOWN")
    layout = mode_def.get("layout", {})
    overrides = mode_def.get("layout_overrides", {})
    size_key = f"{screen_w}x{screen_h}"
    if size_key in overrides:
        layout = _merge_layout_dict(layout, overrides[size_key])
    layout = expand_layout_presets(layout)

    # 1. 状态栏与页脚物理高度测算
    status_bar_pct = 0.10 if screen_h < 200 else 0.12
    status_bar_bottom = int(screen_h * 0.11) + 2 if screen_h <= 128 else int(screen_h * status_bar_pct)

    scale = max(0.92, screen_w / 400.0)
    min_scale = max(0.65, min(scale, screen_h / 300.0))
    ft_layout = layout.get("footer", {})
    footer_height = int(ft_layout.get("height", 30) * min_scale)
    if screen_h <= 128:
        footer_height = max(footer_height, 24)
    footer_top_offset = 3 if screen_h <= 128 else 0
    footer_top = screen_h - footer_height + footer_top_offset

    available_body_height = max(10, footer_top - status_bar_bottom)

    # 2. 构建模拟 RenderContext
    measure_img = Image.new("1", (screen_w, screen_h), EINK_BG)
    ctx = RenderContext(
        draw=ImageDraw.Draw(measure_img),
        img=measure_img,
        content=content,
        screen_w=screen_w,
        screen_h=screen_h,
        y=status_bar_bottom,
        footer_height=footer_height,
        footer_top_offset=footer_top_offset,
        colors=colors,
    )
    apply_text_fontmode(ctx.draw)

    body = layout.get("body", [])
    inspected_blocks: list[BlockInspection] = []
    has_truncation = False
    warnings: list[str] = []

    if _uses_component_tree(body, layout):
        theme = dict(layout.get("component_theme", {}))
        scale = _component_tree_scale(ctx, theme)
        root = _build_component_node(body, content)
        _measure_component_node(root, screen_w, theme, scale)
        root_height = available_body_height if root.kind == "column" else min(available_body_height, root.measured_height)
        _layout_component_node(root, 0, status_bar_bottom, screen_w, root_height, theme, scale)

        def _collect_nodes(node, res: list[BlockInspection]):
            preview = ""
            if getattr(node, "text", None):
                preview = str(node.text)
            elif getattr(node, "props", None) and "text" in node.props:
                preview = str(node.props["text"])
            
            box = getattr(node, "box", None)
            res.append(
                BlockInspection(
                    block_type=getattr(node, "kind", "component"),
                    x=box.x if box else 0,
                    y=box.y if box else status_bar_bottom,
                    width=box.width if box else screen_w,
                    height=box.height if box else root_height,
                    text_preview=preview[:80],
                    rendered_lines=[preview] if preview else [],
                    is_truncated=False,
                )
            )
            for ch in getattr(node, "children", []):
                _collect_nodes(ch, res)

        _collect_nodes(root, inspected_blocks)
        ctx.y = min(footer_top, status_bar_bottom + root.measured_height)
        if root.measured_height > available_body_height:
            has_truncation = True
            warnings.append(f"组件树高度 ({root.measured_height}px) 超出可用主体高度 ({available_body_height}px)。")
    else:
        for idx, block_dict in enumerate(body):
            if not isinstance(block_dict, dict):
                continue
            btype = block_dict.get("type", "unknown")
            start_y = ctx.y

            if ctx.y >= footer_top - 10:
                has_truncation = True
                warnings.append(f"Block #{idx} ({btype}) 达到或超出页脚保护线 ({footer_top}px)，被强制截断未渲染。")
                break

            # 尝试测量文本详情（折行与行数）
            lines: list[str] = []
            text_content = ""
            font_size = int(block_dict.get("font_size", 14) * ctx.scale)
            font_key = block_dict.get("font", "noto_serif_regular")

            field_name = block_dict.get("field")
            if field_name:
                text_content = str(ctx.get_field(field_name))
            else:
                tpl = block_dict.get("template", block_dict.get("text", ""))
                text_content = ctx.resolve(tpl) if tpl else ""

            if text_content and btype in ("text", "centered_text", "icon_text"):
                if has_cjk(text_content):
                    font_key = pick_cjk_font(font_key)
                font = load_font(font_key, font_size)
                max_w = block_dict.get("max_width", ctx.available_width - 32)
                lines = wrap_text(text_content, font, max_w)

            # 执行标准测量推进 y
            w, measured_h = measure_block_size(ctx, block_dict, ctx.available_width)
            # 如果是包含折行的多行文本，按物理分行精准修正高度
            if lines and len(lines) > 1 and btype in ("text", "centered_text"):
                lh = int(block_dict.get("line_height", font_size + 6) * ctx.scale) if block_dict.get("line_height") else (font_size + 6)
                measured_h = max(measured_h, len(lines) * lh)

            # 如果 block 显式设置了 margin_bottom，累加
            mb = int(block_dict.get("margin_bottom", 0) * ctx.scale)
            total_block_h = measured_h + mb

            # 如果测量后突破底部
            block_truncated = False
            if start_y + total_block_h > footer_top:
                has_truncation = True
                block_truncated = True
                warnings.append(
                    f"Block #{idx} ({btype}) 占用高度 {total_block_h}px，超出可用下边界 {start_y + total_block_h - footer_top}px。"
                )

            ctx.y += total_block_h

            inspected_blocks.append(
                BlockInspection(
                    block_type=btype,
                    x=block_dict.get("x", 16),
                    y=start_y,
                    width=w,
                    height=total_block_h,
                    text_preview=text_content[:80],
                    rendered_lines=lines,
                    is_truncated=block_truncated,
                    details={"font_size": font_size, "margin_bottom": mb},
                )
            )

    # 3. 统计指标与密度评估
    body_height_used = min(available_body_height, max(0, ctx.y - status_bar_bottom))
    remaining_height_px = max(0, footer_top - ctx.y)
    fill_ratio = round(body_height_used / float(available_body_height), 3)

    if has_truncation or fill_ratio > 0.92:
        density_assessment = "crowded"
    elif fill_ratio < 0.40:
        density_assessment = "sparse"
    else:
        density_assessment = "balanced"

    if density_assessment == "sparse":
        warnings.append(f"版面空间利用率较低 ({int(fill_ratio * 100)}%)，屏幕下半部分存在较大空白，建议扩充内容或增大字号。")
    elif density_assessment == "crowded" and not has_truncation:
        warnings.append(f"版面较为紧凑 ({int(fill_ratio * 100)}%)，建议注意避免长句溢出。")

    return LayoutSession(
        mode_id=mode_id,
        screen_w=screen_w,
        screen_h=screen_h,
        status_bar_h=status_bar_bottom,
        footer_h=footer_height,
        footer_top=footer_top,
        available_body_height=available_body_height,
        body_height_used=body_height_used,
        remaining_height_px=remaining_height_px,
        fill_ratio=fill_ratio,
        density_assessment=density_assessment,
        has_truncation=has_truncation,
        warnings=warnings,
        blocks=inspected_blocks,
    )


def format_ascii_preview(session: LayoutSession, cols: int = 36, rows: int = 14) -> str:
    """生成 AI 与终端可直接理解的 ASCII 墨水屏空间几何草图。"""
    grid = [[" " for _ in range(cols)] for _ in range(rows)]

    # 顶层状态栏 (占第 1 行)
    sb_str = "[StatusBar]"
    for c in range(cols):
        grid[0][c] = "-"
    start_c = (cols - len(sb_str)) // 2
    for i, ch in enumerate(sb_str):
        grid[0][start_c + i] = ch

    # 底层页脚 (占最后 1 行)
    ft_str = f"[Footer: {session.mode_id[:8]}]"
    for c in range(cols):
        grid[rows - 1][c] = "-"
    start_c = max(1, (cols - len(ft_str)) // 2)
    for i, ch in enumerate(ft_str):
        if start_c + i < cols - 1:
            grid[rows - 1][start_c + i] = ch

    # 中间可用行范围: 1 到 rows - 2
    avail_rows = rows - 2
    body_top = session.status_bar_h
    body_total = session.available_body_height

    for block in session.blocks:
        if body_total <= 0:
            continue
        rel_top = max(0, block.y - body_top)
        rel_bottom = min(body_total, block.y + block.height - body_top)

        start_r = 1 + int((rel_top / float(body_total)) * avail_rows)
        end_r = 1 + int((rel_bottom / float(body_total)) * avail_rows)
        start_r = min(start_r, rows - 2)
        end_r = min(max(start_r, end_r), rows - 2)

        tag = f"<{block.block_type[:6]}>"
        for r in range(start_r, end_r + 1):
            for c in range(2, cols - 2):
                if grid[r][c] == " ":
                    grid[r][c] = "."
        # 在中心填入 tag
        mid_r = (start_r + end_r) // 2
        tc = max(2, (cols - len(tag)) // 2)
        for i, ch in enumerate(tag):
            if tc + i < cols - 2:
                grid[mid_r][tc + i] = ch

    # 渲染带边框的输出
    out_lines = []
    out_lines.append("+" + "-" * (cols) + "+")
    for r in range(rows):
        out_lines.append("|" + "".join(grid[r]) + "|")
    out_lines.append("+" + "-" * (cols) + "+")
    return "\n".join(out_lines)


def format_ai_dialogue(session: LayoutSession) -> str:
    """生成供 AI Agent 或大模型直接理解与消费的语义排版会话诊断报告。"""
    ascii_mockup = format_ascii_preview(session)
    status_emoji = "✅ 优秀" if session.density_assessment == "balanced" and not session.has_truncation else (
        "❌ 截断警告" if session.has_truncation else "⚠️ 留白过多"
    )

    lines = [
        "### 墨水屏物理版面诊断报告 (AI-Readable Layout Inspection)",
        f"- **模式标识**: `{session.mode_id}`",
        f"- **物理屏幕分辨率**: {session.screen_w}x{session.screen_h} (1-bit E-ink)",
        f"- **排版状态**: {status_emoji} (密度评定: `{session.density_assessment}`)",
        f"- **空间利用率**: {int(session.fill_ratio * 100)}% (主体占用: {session.body_height_used}px / 可用: {session.available_body_height}px)",
        f"- **剩余保护余量**: {session.remaining_height_px}px",
        f"- **是否发生截断**: {'是 (存在文字丢失)' if session.has_truncation else '否 (全部内容完整显示)'}",
        "",
        "#### 🖥️ 版面拓扑预览 (ASCII Spatial Mockup):",
        "```text",
        ascii_mockup,
        "```",
        "",
        "#### 📦 区块物理分布明细:",
    ]

    for idx, b in enumerate(session.blocks):
        trunc_flag = " ⚠️[TRUNCATED]" if b.is_truncated else ""
        lines.append(
            f"{idx + 1}. **[{b.block_type}]** Y={b.y}px ~ {b.y + b.height}px (H={b.height}px){trunc_flag}"
        )
        if b.rendered_lines:
            lines.append(f"   - 实际折行数: {len(b.rendered_lines)} 行")
            preview = " / ".join(b.rendered_lines[:3])
            lines.append(f"   - 排版文本: \"{preview}\"")

    lines.append("")
    lines.append("#### 🤖 AI 排版优化建议:")
    if session.has_truncation:
        lines.append("1. **紧急处理**: 内容文本超出了物理屏幕高度，末尾已被粗暴裁切！")
        lines.append("2. **降容建议**: 请将生成文本字数缩减 20%~30%，或者降低字号（如 16px -> 14px）。")
    elif session.density_assessment == "sparse":
        lines.append("1. **美化建议**: 墨水屏下半部分留白率过高 (>50%)，缺乏视觉重心。")
        lines.append("2. **增容建议**: 可适当丰富内容表述，或增加辅助解读、副标题或加大主文字字号。")
    else:
        lines.append("1. **排版极佳**: 视觉比例协调，字符密度舒适，未触碰边界安全线。")

    if session.warnings:
        lines.append("")
        lines.append("#### ⚠️ 警告事项:")
        for w in session.warnings:
            lines.append(f"- {w}")

    return "\n".join(lines)
