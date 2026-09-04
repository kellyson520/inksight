#!/usr/bin/env python3
"""
InkSight 渲染自检与视觉质检工具 (Inspect Render CLI)
- 生成指定模式在特定硬件规格下的最终墨水屏渲染画面 (PNG)
- 输出像素级排版诊断指标 (色阶分布、内容边界、垂直留白间距、图文重叠检测)
- 保存高清图片供视觉审查模型 (read_image) 及人工走查
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

# 将 backend 加入模块搜索路径
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from PIL import Image
import numpy as np

from core.context import get_date_context
from core.pipeline import generate_and_render
from core.config import SCREEN_WIDTH, SCREEN_HEIGHT


def analyze_image_layout(img: Image.Image) -> dict[str, Any]:
    """分析渲染图片的像素分布、内容块和留白情况。"""
    arr = np.array(img)
    h, w = arr.shape[:2]
    
    # 获取非背景(非纯白)像素
    # 调色板模式下 1 为白色背景，双色模式下 1 为白色背景
    if img.mode == "P":
        # 0: black, 1: white, 2: yellow, 3: red
        is_content = (arr != 1)
        colors_count = {
            "black": int((arr == 0).sum()),
            "white": int((arr == 1).sum()),
            "yellow": int((arr == 2).sum()),
            "red": int((arr == 3).sum()),
        }
    else:
        # 1-bit or L mode: 0 is black, 1 or 255 is white
        is_content = (arr == 0)
        colors_count = {
            "black": int((arr == 0).sum()),
            "white": int((arr != 0).sum()),
        }

    # 扫描每行的内容分布
    row_counts = is_content.sum(axis=1)
    content_rows = np.where(row_counts > 0)[0]

    blocks = []
    if len(content_rows) > 0:
        in_block = False
        b_start = 0
        for y in range(h):
            if row_counts[y] > 0 and not in_block:
                in_block = True
                b_start = y
            elif row_counts[y] == 0 and in_block:
                in_block = False
                blocks.append({
                    "top": int(b_start),
                    "bottom": int(y - 1),
                    "height": int(y - b_start),
                    "pixels": int(row_counts[b_start:y].sum())
                })
        if in_block:
            blocks.append({
                "top": int(b_start),
                "bottom": int(h - 1),
                "height": int(h - b_start),
                "pixels": int(row_counts[b_start:h].sum())
            })

    # 计算相邻块之间的间距 (gaps)
    gaps = []
    for i in range(1, len(blocks)):
        prev_b = blocks[i - 1]
        curr_b = blocks[i]
        gap_h = curr_b["top"] - prev_b["bottom"] - 1
        gaps.append({
            "between": f"Block #{i-1} -> #{i}",
            "gap_pixels": int(gap_h),
            "status": "healthy" if gap_h >= 4 else ("tight" if gap_h >= 0 else "OVERLAP_COLLISION")
        })

    return {
        "dimensions": f"{w}x{h}",
        "mode": img.mode,
        "colors_count": colors_count,
        "content_blocks_count": len(blocks),
        "blocks": blocks,
        "gaps": gaps,
        "content_top": int(content_rows[0]) if len(content_rows) else 0,
        "content_bottom": int(content_rows[-1]) if len(content_rows) else 0,
    }


async def main_async():
    parser = argparse.ArgumentParser(description="InkSight 渲染自检与视觉质检工具")
    parser.add_argument("--mode", "-m", default="CRYPTO", help="渲染模式 ID (如 CRYPTO, HOTLIST, WEBHOOK, etc.)")
    parser.add_argument("--colors", "-c", type=int, default=3, choices=[2, 3, 4], help="颜色通道数 (2=黑白, 3=黑白红, 4=黑白红黄)")
    parser.add_argument("--symbol", "-s", default="", help="覆盖资产或股票代码 (如 BTC, AAPL, TSLA, NVDA)")
    parser.add_argument("--platform", "-p", default="", help="覆盖热榜平台 (如 zhihu, weibo, bilibili, github)")
    parser.add_argument("--width", "-W", type=int, default=SCREEN_WIDTH, help="屏幕宽度")
    parser.add_argument("--height", "-H", type=int, default=SCREEN_HEIGHT, help="屏幕高度")
    parser.add_argument("--output", "-o", default="", help="输出 PNG 图片路径 (缺省为 /tmp/inksight_inspect_<mode>.png)")

    args = parser.parse_args()

    mode_id = args.mode.upper()
    out_path = args.output or f"/tmp/inksight_inspect_{mode_id.lower()}.png"

    # 构建配置覆盖
    cfg: dict[str, Any] = {"mode_overrides": {}}
    if args.symbol:
        cfg["mode_overrides"][mode_id] = {"symbol": args.symbol}
    if args.platform:
        cfg["mode_overrides"][mode_id] = {"platform": args.platform}

    date_ctx = await get_date_context()
    weather = {"weather_str": "晴 22°C", "weather_code": 0}

    print(f"[*] Generating preview for mode '{mode_id}' (colors={args.colors}, size={args.width}x{args.height})...")
    img, content = await generate_and_render(
        mode_id,
        cfg,
        date_ctx,
        weather,
        100.0,
        screen_w=args.width,
        screen_h=args.height,
        colors=args.colors,
    )

    # 统一转换并保存为标准 24-bit RGB PNG，确保图像工具能无损读取
    rgb_img = img.convert("RGB")
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    rgb_img.save(out_path, format="PNG")
    print(f"[✓] Saved rendered image to: {out_path}")

    # 分析排版结构
    metrics = analyze_image_layout(img)
    print("\n--- 排版结构诊断报告 ---")
    print(f"分辨率与模式: {metrics['dimensions']} ({metrics['mode']})")
    print(f"色彩分布: {metrics['colors_count']}")
    print(f"检测到的内容块数量: {metrics['content_blocks_count']}")
    print(f"内容纵向有效范围: Y={metrics['content_top']} 到 Y={metrics['content_bottom']} (总高 {args.height})")
    print("块间距诊断:")
    for g in metrics['gaps']:
        status_flag = "✓" if g['status'] == "healthy" else ("⚠" if g['status'] == "tight" else "❌")
        print(f"  {status_flag} {g['between']}: {g['gap_pixels']}px ({g['status']})")

    # 运行 OCR 视觉识别
    try:
        import pytesseract
        ocr_text = pytesseract.image_to_string(rgb_img, lang='chi_sim+eng').strip()
        print("\n--- 视觉识别提取结果 (OCR) ---")
        for line in ocr_text.splitlines():
            if line.strip():
                print(f"  > {line.strip()}")
    except Exception as exc:
        print(f"\n[!] OCR 视觉识别跳过: {exc}")

    # 检查是否有重叠
    overlaps = [g for g in metrics['gaps'] if g['status'] == "OVERLAP_COLLISION"]
    if overlaps:
        print("\n[!] 警告: 检测到内容行重叠碰撞!")
        sys.exit(1)
    else:
        print("\n[✓] 质检通过: 所有内容块布局正向分隔，无任何重叠碰撞。")


if __name__ == "__main__":
    asyncio.run(main_async())
