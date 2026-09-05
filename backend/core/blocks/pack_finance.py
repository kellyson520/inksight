"""
InkSight 扩充排版组件库 3：金融证券与资产行情组件 (Finance & Market Widgets)
包含：
31. stock_ticker_tape: 紧凑股票滚动跑马灯行
32. depth_chart_bar: 买卖单深度对比条
33. crypto_ratio_gauge: 多空比与贪婪恐慌量规
34. forex_pair_row: 外汇货币对汇率排版行
35. dividend_yield_badge: 股息率与收益率徽章
36. pnl_change_capsule: 盈亏与绝对收益变动胶囊
37. market_cap_rank: 市值排名与行业标签
38. rsi_indicator_line: RSI 相对强弱指标超买超卖线
39. macd_histogram_mini: MACD 柱状图微型走势
40. volume_profile_bar: 成交量分布横向柱
41. orderbook_mini_row: 极简盘口买一卖一档位
42. bond_yield_curve_dot: 国债收益率基点利差
43. gold_silver_ratio: 金银比率指示器
44. gas_tracker_badge: 以太坊 Gas Gwei 指示器
45. liquidation_alert_strip: 大额强平预警条
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


@register_block("stock_ticker_tape")
def render_stock_ticker_tape(ctx: RenderContext, block: dict) -> None:
    """股票跑马灯简报行。"""
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 4) * ctx.scale)
    sym = str(block.get("symbol", "NVDA"))
    p = str(block.get("price", "$124.50"))
    chg = str(block.get("change", "+3.2%"))
    x = ctx.x_offset + margin_x
    y = ctx.y

    font_b = load_font("noto_serif_bold", int(9 * ctx.scale))
    font_r = load_font("noto_serif_regular", int(9 * ctx.scale))
    ctx.draw.text((x, y), sym, fill=EINK_FG, font=font_b)
    ctx.draw.text((x + 46, y), p, fill=EINK_FG, font=font_r)
    ctx.draw.text((x + 105, y), chg, fill=EINK_FG, font=font_b)
    ctx.y = y + 14 + margin_bottom


@register_block("depth_chart_bar")
def render_depth_chart_bar(ctx: RenderContext, block: dict) -> None:
    """买卖单深度对比条。"""
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 6) * ctx.scale)
    bid_pct = float(block.get("bid", 56.0))
    w = ctx.available_width - margin_x * 2
    x = ctx.x_offset + margin_x
    y = ctx.y

    font = load_font("noto_serif_regular", int(8 * ctx.scale))
    ctx.draw.text((x, y), f"BIDS: {bid_pct:.0f}%", fill=EINK_FG, font=font)
    ctx.draw.text((x + w - 46, y), f"ASKS: {100-bid_pct:.0f}%", fill=EINK_FG, font=font)
    by = y + 12
    _draw_box(ctx.draw, (x, by, x + w, by + 6), outline=EINK_FG, width=1)
    bw = int(w * (bid_pct / 100.0))
    if bw > 0:
        _draw_box(ctx.draw, (x, by, x + bw, by + 6), fill=EINK_FG)
    ctx.y = by + 8 + margin_bottom


@register_block("crypto_ratio_gauge")
def render_crypto_ratio_gauge(ctx: RenderContext, block: dict) -> None:
    """多空比与贪婪恐慌量规。"""
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 6) * ctx.scale)
    score = int(block.get("score", 74))
    text = str(block.get("text", "GREED"))
    x = ctx.x_offset + margin_x
    y = ctx.y

    font = load_font("noto_serif_bold", int(10 * ctx.scale))
    ctx.draw.text((x, y), f"SENTIMENT: {score} [{text}]", fill=EINK_FG, font=font)
    ctx.y = y + 14 + margin_bottom


@register_block("forex_pair_row")
def render_forex_pair_row(ctx: RenderContext, block: dict) -> None:
    """外汇货币对汇率行。"""
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 4) * ctx.scale)
    pair = str(block.get("pair", "USD/CNY"))
    rate = str(block.get("rate", "7.1420"))
    x = ctx.x_offset + margin_x
    y = ctx.y

    font_b = load_font("noto_serif_bold", int(9 * ctx.scale))
    font_r = load_font("noto_serif_regular", int(9 * ctx.scale))
    ctx.draw.text((x, y), pair, fill=EINK_FG, font=font_b)
    ctx.draw.text((x + 70, y), rate, fill=EINK_FG, font=font_r)
    ctx.y = y + 14 + margin_bottom


@register_block("dividend_yield_badge")
def render_dividend_yield_badge(ctx: RenderContext, block: dict) -> None:
    """股息率与收益率徽章。"""
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 4) * ctx.scale)
    div_str = str(block.get("yield_str", "DIV: 3.45%"))
    x = ctx.x_offset + margin_x
    y = ctx.y

    font = load_font("noto_serif_regular", int(8 * ctx.scale))
    tb = safe_font_bbox(font, div_str)
    bw = (tb[2] - tb[0]) + 8
    _draw_box(ctx.draw, (x, y, x + bw, y + 12), outline=EINK_FG, width=1)
    ctx.draw.text((x + 4, y + 1), div_str, fill=EINK_FG, font=font)
    ctx.y = y + 14 + margin_bottom


@register_block("pnl_change_capsule")
def render_pnl_change_capsule(ctx: RenderContext, block: dict) -> None:
    """盈亏收益变动胶囊。"""
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 4) * ctx.scale)
    pnl = str(block.get("pnl", "+$1,240.50 (+4.8%)"))
    x = ctx.x_offset + margin_x
    y = ctx.y

    font = load_font("noto_serif_bold", int(9 * ctx.scale))
    tb = safe_font_bbox(font, pnl)
    bw = (tb[2] - tb[0]) + 10
    _draw_box(ctx.draw, (x, y, x + bw, y + 14), fill=EINK_FG)
    ctx.draw.text((x + 5, y + 1), pnl, fill=EINK_BG, font=font)
    ctx.y = y + 16 + margin_bottom


@register_block("market_cap_rank")
def render_market_cap_rank(ctx: RenderContext, block: dict) -> None:
    """市值排名与标签。"""
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 4) * ctx.scale)
    rank = str(block.get("rank", "#1"))
    cap = str(block.get("cap", "$3.24T"))
    x = ctx.x_offset + margin_x
    y = ctx.y

    font = load_font("noto_serif_regular", int(9 * ctx.scale))
    ctx.draw.text((x, y), f"RANK {rank} · MCAP {cap}", fill=EINK_FG, font=font)
    ctx.y = y + 13 + margin_bottom


@register_block("rsi_indicator_line")
def render_rsi_indicator_line(ctx: RenderContext, block: dict) -> None:
    """RSI 相对强弱指标线。"""
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 6) * ctx.scale)
    val = float(block.get("rsi", 62.0))
    x = ctx.x_offset + margin_x
    y = ctx.y
    w = ctx.available_width - margin_x * 2

    font = load_font("noto_serif_regular", int(8 * ctx.scale))
    ctx.draw.text((x, y), f"RSI(14): {val:.1f}", fill=EINK_FG, font=font)
    by = y + 12
    _draw_box(ctx.draw, (x, by, x + w, by + 4), outline=EINK_FG, width=1)
    # 标出 30/70 虚线刻度
    x30 = x + int(w * 0.3)
    x70 = x + int(w * 0.7)
    ctx.draw.line((x30, by - 1, x30, by + 5), fill=EINK_FG, width=1)
    ctx.draw.line((x70, by - 1, x70, by + 5), fill=EINK_FG, width=1)
    # 点位
    px = x + int(w * (val / 100.0))
    ctx.draw.ellipse((px - 2, by - 1, px + 2, by + 5), fill=EINK_FG)
    ctx.y = by + 7 + margin_bottom


@register_block("macd_histogram_mini")
def render_macd_histogram_mini(ctx: RenderContext, block: dict) -> None:
    """MACD 迷你柱状走势。"""
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 6) * ctx.scale)
    bars = block.get("bars") or [-4, -2, 1, 3, 5, 4, 2, -1, -3]
    x = ctx.x_offset + margin_x
    y = ctx.y
    mid_y = y + 10

    ctx.draw.line((x, mid_y, x + 60, mid_y), fill=EINK_FG, width=1)
    for i, b in enumerate(bars):
        bx = x + i * 6
        if b >= 0:
            _draw_box(ctx.draw, (bx, mid_y - b * 2, bx + 4, mid_y), fill=EINK_FG)
        else:
            _draw_box(ctx.draw, (bx, mid_y, bx + 4, mid_y - b * 2), outline=EINK_FG, width=1)
    ctx.y = y + 22 + margin_bottom


@register_block("volume_profile_bar")
def render_volume_profile_bar(ctx: RenderContext, block: dict) -> None:
    """成交量分布横向柱。"""
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 4) * ctx.scale)
    vol = str(block.get("volume", "VOL: 42.8M"))
    x = ctx.x_offset + margin_x
    y = ctx.y

    font = load_font("noto_serif_regular", int(9 * ctx.scale))
    ctx.draw.text((x, y), vol, fill=EINK_FG, font=font)
    ctx.y = y + 13 + margin_bottom


@register_block("orderbook_mini_row")
def render_orderbook_mini_row(ctx: RenderContext, block: dict) -> None:
    """极简盘口档位行。"""
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 4) * ctx.scale)
    bid_p = str(block.get("bid_p", "957.90"))
    ask_p = str(block.get("ask_p", "958.00"))
    x = ctx.x_offset + margin_x
    y = ctx.y

    font = load_font("noto_serif_regular", int(8 * ctx.scale))
    ctx.draw.text((x, y), f"BID1: {bid_p} | ASK1: {ask_p}", fill=EINK_FG, font=font)
    ctx.y = y + 12 + margin_bottom


@register_block("bond_yield_curve_dot")
def render_bond_yield_curve_dot(ctx: RenderContext, block: dict) -> None:
    """国债收益率利差行。"""
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 4) * ctx.scale)
    y10 = str(block.get("us10y", "4.28%"))
    y2 = str(block.get("us2y", "3.92%"))
    x = ctx.x_offset + margin_x
    y = ctx.y

    font = load_font("noto_serif_regular", int(9 * ctx.scale))
    ctx.draw.text((x, y), f"10Y: {y10} / 2Y: {y2} (SPREAD: +36bp)", fill=EINK_FG, font=font)
    ctx.y = y + 13 + margin_bottom


@register_block("gold_silver_ratio")
def render_gold_silver_ratio(ctx: RenderContext, block: dict) -> None:
    """金银比率指示器。"""
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 4) * ctx.scale)
    ratio = str(block.get("ratio", "86.4"))
    x = ctx.x_offset + margin_x
    y = ctx.y

    font = load_font("noto_serif_bold", int(9 * ctx.scale))
    ctx.draw.text((x, y), f"AU/AG RATIO: {ratio}", fill=EINK_FG, font=font)
    ctx.y = y + 13 + margin_bottom


@register_block("gas_tracker_badge")
def render_gas_tracker_badge(ctx: RenderContext, block: dict) -> None:
    """以太坊 Gas 价格徽章。"""
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 4) * ctx.scale)
    gwei = str(block.get("gwei", "12 Gwei"))
    x = ctx.x_offset + margin_x
    y = ctx.y

    font = load_font("noto_serif_regular", int(8 * ctx.scale))
    tb = safe_font_bbox(font, f"GAS: {gwei}")
    bw = (tb[2] - tb[0]) + 8
    _draw_box(ctx.draw, (x, y, x + bw, y + 12), outline=EINK_FG, width=1)
    ctx.draw.text((x + 4, y + 1), f"GAS: {gwei}", fill=EINK_FG, font=font)
    ctx.y = y + 14 + margin_bottom


@register_block("liquidation_alert_strip")
def render_liquidation_alert_strip(ctx: RenderContext, block: dict) -> None:
    """大额强平与爆仓预警条。"""
    margin_x = int(block.get("margin_x", 14) * ctx.scale)
    margin_bottom = int(block.get("margin_bottom", 4) * ctx.scale)
    amount = str(block.get("amount", "$14.2M Longs Liq"))
    x = ctx.x_offset + margin_x
    y = ctx.y
    w = ctx.available_width - margin_x * 2

    font = load_font("noto_serif_regular", int(8 * ctx.scale))
    _draw_box(ctx.draw, (x, y, x + w, y + 14), outline=EINK_FG, width=1)
    ctx.draw.text((x + 6, y + 1), f"ALERT: {amount}", fill=EINK_FG, font=font)
    ctx.y = y + 16 + margin_bottom
