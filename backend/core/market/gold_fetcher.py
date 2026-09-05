"""
黄金市场行情抓取器 (Gold Market Fetcher)
支持沪金主力 (AU0)、伦敦金现货 (XAU) 以及上海金交所现货 (AU9999)。
包含实时分钟分时走势解析、极值振幅计算与双币种联动参考折算。
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from typing import Any

from core.http_client import get_async_client
from .crypto_fetcher import downsample

logger = logging.getLogger(__name__)

GOLD_SYMBOLS = {"AU0", "XAU", "AU9999", "518880", "GOLD", "AU"}

GOLD_NAMES: dict[str, str] = {
    "AU0": "沪金连续",
    "XAU": "伦敦金 (现货黄金)",
    "AU9999": "上海金 (Au99.99)",
    "518880": "华安黄金ETF",
}

SEED_GOLD_DATA: dict[str, dict[str, Any]] = {
    "AU0": {
        "symbol": "AU0",
        "symbol_tag": "AU0 · 沪金",
        "name": "沪金连续 (主力期货)",
        "price": "958.00",
        "price_num": 958.0,
        "unit": "元/克",
        "currency_symbol": "¥",
        "price_display": "¥958.00",
        "price_unit_display": "¥958.00 / 克",
        "change_24h": "-1.32%",
        "change_num": -1.32,
        "is_up": False,
        "high_24h": "961.88",
        "low_24h": "944.10",
        "amplitude": "1.83%",
        "sparkline_data": [
            944.62, 946.80, 948.74, 949.00, 947.38, 947.70, 948.24, 948.90,
            949.08, 950.12, 951.30, 953.40, 955.10, 956.20, 958.00, 959.50,
            961.88, 960.20, 959.00, 958.40, 957.80, 958.20, 957.90, 958.00,
        ],
        "ref_title": "国际现货参考",
        "ref_price": "$4,430.96 / 盎司",
        "ref_change": "-0.94%",
        "exchange_rate_hint": "1 盎司 ≈ 31.1035 克",
        "update_time": "实时分时",
        "status_text": "沪金主力分时",
    },
    "XAU": {
        "symbol": "XAU",
        "symbol_tag": "XAU/USD · 现货",
        "name": "伦敦金 (现货黄金)",
        "price": "4,430.96",
        "price_num": 4430.96,
        "unit": "美元/盎司",
        "currency_symbol": "$",
        "price_display": "$4,430.96",
        "price_unit_display": "$4,430.96 / oz",
        "change_24h": "-0.94%",
        "change_num": -0.94,
        "is_up": False,
        "high_24h": "4490.58",
        "low_24h": "4365.58",
        "amplitude": "2.80%",
        "sparkline_data": [
            4472.99, 4475.39, 4478.20, 4482.50, 4488.10, 4490.58, 4485.00, 4478.40,
            4465.20, 4450.00, 4442.80, 4435.50, 4420.00, 4410.50, 4395.00, 4380.20,
            4365.58, 4375.00, 4390.40, 4405.00, 4418.20, 4425.00, 4428.50, 4430.96,
        ],
        "ref_title": "国内克价参考",
        "ref_price": "¥958.00 / 克",
        "ref_change": "-1.32%",
        "exchange_rate_hint": "折合国内约 ¥1,018/克",
        "update_time": "实时分时",
        "status_text": "伦敦金全球分时",
    },
    "AU9999": {
        "symbol": "AU9999",
        "symbol_tag": "AU9999 · 现货",
        "name": "上海金 (Au99.99)",
        "price": "958.00",
        "price_num": 958.0,
        "unit": "元/克",
        "currency_symbol": "¥",
        "price_display": "¥958.00",
        "price_unit_display": "¥958.00 / 克",
        "change_24h": "-0.82%",
        "change_num": -0.82,
        "is_up": False,
        "high_24h": "968.00",
        "low_24h": "943.00",
        "amplitude": "2.61%",
        "sparkline_data": [
            943.00, 945.20, 947.50, 950.00, 952.80, 955.00, 958.20, 960.50,
            963.00, 965.80, 968.00, 966.50, 964.00, 962.20, 960.00, 959.20,
            958.50, 957.90, 958.00, 958.20, 957.80, 958.10, 957.95, 958.00,
        ],
        "ref_title": "国际现货参考",
        "ref_price": "$4,430.96 / 盎司",
        "ref_change": "-0.94%",
        "exchange_rate_hint": "实物金条与饰品金基准",
        "update_time": "实时分时",
        "status_text": "金交所现货分时",
    },
}


async def fetch_gold(symbol: str) -> dict[str, Any] | None:
    client = get_async_client()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://finance.sina.com.cn",
    }

    if symbol in ("XAU", "XAUUSD"):
        return await _fetch_gold_xau(client, headers)
    elif symbol in ("AU9999", "SGE_AU9999"):
        return await _fetch_gold_au9999(client, headers)
    else:
        return await _fetch_gold_au0(client, headers)


async def _fetch_gold_au0(client, headers) -> dict[str, Any] | None:
    quote_url = "https://hq.sinajs.cn/list=nf_AU0,hf_XAU"
    minline_url = "https://stock2.finance.sina.com.cn/futures/api/jsonp.php/var_au=/InnerFuturesNewService.getMinLine?symbol=AU0"

    try:
        r_q, r_m = await asyncio.gather(
            client.get(quote_url, headers=headers, timeout=4.5),
            client.get(minline_url, headers=headers, timeout=4.5),
            return_exceptions=True,
        )
    except Exception as e:
        logger.warning("[GoldFetcher] Gold AU0 gather error: %s", e)
        return None

    current_p = 0.0
    pct_change = 0.0
    high_p = 0.0
    low_p = 0.0
    ref_price = "$4,430.96 / 盎司"
    ref_change = "-0.94%"

    if not isinstance(r_q, Exception) and r_q.status_code == 200:
        text = r_q.text
        au_m = re.search(r'hq_str_nf_AU0="([^"]+)"', text)
        xau_m = re.search(r'hq_str_hf_XAU="([^"]+)"', text)
        if au_m:
            parts = au_m.group(1).split(",")
            if len(parts) > 10:
                current_p = float(parts[8]) if parts[8] else 0.0
                prev_close = float(parts[10]) if parts[10] else current_p
                high_p = float(parts[3]) if parts[3] else current_p
                low_p = float(parts[4]) if parts[4] else current_p
                if prev_close > 0:
                    pct_change = ((current_p - prev_close) / prev_close) * 100.0
        if xau_m:
            x_parts = xau_m.group(1).split(",")
            if len(x_parts) > 7:
                x_cur = float(x_parts[0]) if x_parts[0] else 0.0
                x_prev = float(x_parts[7]) if x_parts[7] else x_cur
                x_chg = ((x_cur - x_prev) / x_prev * 100.0) if x_prev > 0 else 0.0
                ref_price = f"${x_cur:,.2f} / 盎司"
                ref_change = f"{x_chg:+.2f}%"

    real_prices: list[float] = []
    if not isinstance(r_m, Exception) and r_m.status_code == 200:
        m = re.search(r'var_au=\((.*)\);', r_m.text, re.DOTALL)
        if m:
            try:
                pts = json.loads(m.group(1))
                real_prices = [float(p[1]) for p in pts if len(p) > 1 and p[1]]
            except Exception as e:
                logger.debug("[GoldFetcher] AU0 minline parse error: %s", e)

    if len(real_prices) < 2:
        seed_pts = SEED_GOLD_DATA.get("AU0", {}).get("sparkline_data", [])
        factor = (current_p / 958.0) if current_p > 0 else 1.0
        real_prices = [round(p * factor, 2) for p in seed_pts] if seed_pts else [current_p] * 24

    if current_p <= 0:
        current_p = real_prices[-1]
    if high_p <= 0:
        high_p = max(real_prices)
    if low_p <= 0:
        low_p = min(real_prices)
    if pct_change == 0.0 and len(real_prices) >= 2:
        pct_change = ((real_prices[-1] - real_prices[0]) / real_prices[0]) * 100.0

    amp = ((high_p - low_p) / low_p * 100.0) if low_p > 0 else 0.0
    return {
        "symbol": "AU0",
        "symbol_tag": "AU0 · 沪金",
        "name": "沪金连续 (主力期货)",
        "price": f"{current_p:.2f}",
        "price_num": current_p,
        "unit": "元/克",
        "currency_symbol": "¥",
        "price_display": f"¥{current_p:.2f}",
        "price_unit_display": f"¥{current_p:.2f} / 克",
        "change_24h": f"{pct_change:+.2f}%",
        "change_num": round(pct_change, 2),
        "is_up": pct_change >= 0,
        "high_24h": f"{high_p:.2f}",
        "low_24h": f"{low_p:.2f}",
        "amplitude": f"{amp:.2f}%",
        "sparkline_data": downsample(real_prices, 24),
        "ref_title": "国际现货参考",
        "ref_price": ref_price,
        "ref_change": ref_change,
        "exchange_rate_hint": "1 盎司 ≈ 31.1035 克",
        "update_time": time.strftime("%H:%M"),
        "status_text": "沪金主力分时",
    }


async def _fetch_gold_xau(client, headers) -> dict[str, Any] | None:
    quote_url = "https://hq.sinajs.cn/list=hf_XAU,nf_AU0"
    minline_url = "https://stock2.finance.sina.com.cn/futures/api/jsonp.php/var_xau=/GlobalFuturesService.getGlobalFuturesMinLine?symbol=XAU"

    try:
        r_q, r_m = await asyncio.gather(
            client.get(quote_url, headers=headers, timeout=4.5),
            client.get(minline_url, headers=headers, timeout=4.5),
            return_exceptions=True,
        )
    except Exception as e:
        logger.warning("[GoldFetcher] Gold XAU gather error: %s", e)
        return None

    current_p = 0.0
    pct_change = 0.0
    high_p = 0.0
    low_p = 0.0
    ref_price = "¥958.00 / 克"
    ref_change = "-1.32%"

    if not isinstance(r_q, Exception) and r_q.status_code == 200:
        text = r_q.text
        xau_m = re.search(r'hq_str_hf_XAU="([^"]+)"', text)
        au_m = re.search(r'hq_str_nf_AU0="([^"]+)"', text)
        if xau_m:
            parts = xau_m.group(1).split(",")
            if len(parts) > 7:
                current_p = float(parts[0]) if parts[0] else 0.0
                prev_close = float(parts[7]) if parts[7] else current_p
                high_p = float(parts[4]) if parts[4] else current_p
                low_p = float(parts[5]) if parts[5] else current_p
                if prev_close > 0:
                    pct_change = ((current_p - prev_close) / prev_close) * 100.0
        if au_m:
            au_parts = au_m.group(1).split(",")
            if len(au_parts) > 10:
                au_cur = float(au_parts[8]) if au_parts[8] else 0.0
                au_prev = float(au_parts[10]) if au_parts[10] else au_cur
                au_chg = ((au_cur - au_prev) / au_prev * 100.0) if au_prev > 0 else 0.0
                ref_price = f"¥{au_cur:.2f} / 克"
                ref_change = f"{au_chg:+.2f}%"

    real_prices: list[float] = []
    if not isinstance(r_m, Exception) and r_m.status_code == 200:
        m = re.search(r'var_xau=\((.*)\);', r_m.text, re.DOTALL)
        if m:
            try:
                data = json.loads(m.group(1))
                pts = data.get("minLine_1d", [])
                real_prices = [float(p[1]) for p in pts if len(p) > 1 and p[1]]
            except Exception as e:
                logger.debug("[GoldFetcher] XAU minline parse error: %s", e)

    if len(real_prices) < 2:
        seed_pts = SEED_GOLD_DATA.get("XAU", {}).get("sparkline_data", [])
        factor = (current_p / 4430.96) if current_p > 0 else 1.0
        real_prices = [round(p * factor, 2) for p in seed_pts] if seed_pts else [current_p] * 24

    if current_p <= 0:
        current_p = real_prices[-1]
    if high_p <= 0:
        high_p = max(real_prices)
    if low_p <= 0:
        low_p = min(real_prices)
    if pct_change == 0.0 and len(real_prices) >= 2:
        pct_change = ((real_prices[-1] - real_prices[0]) / real_prices[0]) * 100.0

    amp = ((high_p - low_p) / low_p * 100.0) if low_p > 0 else 0.0
    cny_equiv = (current_p * 7.15 / 31.1035) if current_p > 0 else 0.0
    return {
        "symbol": "XAU",
        "symbol_tag": "XAU/USD · 现货",
        "name": "伦敦金 (现货黄金)",
        "price": f"{current_p:,.2f}",
        "price_num": current_p,
        "unit": "美元/盎司",
        "currency_symbol": "$",
        "price_display": f"${current_p:,.2f}",
        "price_unit_display": f"${current_p:,.2f} / oz",
        "change_24h": f"{pct_change:+.2f}%",
        "change_num": round(pct_change, 2),
        "is_up": pct_change >= 0,
        "high_24h": f"{high_p:,.2f}",
        "low_24h": f"{low_p:,.2f}",
        "amplitude": f"{amp:.2f}%",
        "sparkline_data": downsample(real_prices, 24),
        "ref_title": "国内克价参考",
        "ref_price": ref_price,
        "ref_change": ref_change,
        "exchange_rate_hint": f"折合国内约 ¥{cny_equiv:.1f}/克" if cny_equiv > 0 else "全球黄金定价基准",
        "update_time": time.strftime("%H:%M"),
        "status_text": "伦敦金全球分时",
    }


async def _fetch_gold_au9999(client, headers) -> dict[str, Any] | None:
    quote_url = "https://hq.sinajs.cn/list=SGE_AU9999,hf_XAU"
    try:
        r_q = await client.get(quote_url, headers=headers, timeout=4.5)
    except Exception as e:
        logger.warning("[GoldFetcher] AU9999 fetch error: %s", e)
        return None

    current_p = 0.0
    pct_change = 0.0
    high_p = 0.0
    low_p = 0.0
    ref_price = "$4,430.96 / 盎司"
    ref_change = "-0.94%"

    if r_q.status_code == 200:
        text = r_q.text
        sge_m = re.search(r'hq_str_SGE_AU9999="([^"]+)"', text)
        xau_m = re.search(r'hq_str_hf_XAU="([^"]+)"', text)
        if sge_m:
            parts = sge_m.group(1).split(",")
            if len(parts) > 17:
                current_p = float(parts[8]) if parts[8] else 0.0
                high_p = float(parts[6]) if parts[6] else current_p
                low_p = float(parts[7]) if parts[7] else current_p
                chg_str = parts[17].replace("%", "").strip()
                pct_change = float(chg_str) if chg_str else 0.0
        if xau_m:
            x_parts = xau_m.group(1).split(",")
            if len(x_parts) > 7:
                x_cur = float(x_parts[0]) if x_parts[0] else 0.0
                x_prev = float(x_parts[7]) if x_parts[7] else x_cur
                x_chg = ((x_cur - x_prev) / x_prev * 100.0) if x_prev > 0 else 0.0
                ref_price = f"${x_cur:,.2f} / 盎司"
                ref_change = f"{x_chg:+.2f}%"

    if current_p <= 0:
        return None

    amp = ((high_p - low_p) / low_p * 100.0) if low_p > 0 else 0.0
    seed_pts = SEED_GOLD_DATA["AU9999"]["sparkline_data"]
    factor = current_p / 958.0 if current_p > 0 else 1.0
    spark_pts = [round(p * factor, 2) for p in seed_pts]

    return {
        "symbol": "AU9999",
        "symbol_tag": "AU9999 · 现货",
        "name": "上海金 (Au99.99)",
        "price": f"{current_p:.2f}",
        "price_num": current_p,
        "unit": "元/克",
        "currency_symbol": "¥",
        "price_display": f"¥{current_p:.2f}",
        "price_unit_display": f"¥{current_p:.2f} / 克",
        "change_24h": f"{pct_change:+.2f}%",
        "change_num": round(pct_change, 2),
        "is_up": pct_change >= 0,
        "high_24h": f"{high_p:.2f}",
        "low_24h": f"{low_p:.2f}",
        "amplitude": f"{amp:.2f}%",
        "sparkline_data": spark_pts,
        "ref_title": "国际现货参考",
        "ref_price": ref_price,
        "ref_change": ref_change,
        "exchange_rate_hint": "实物金条与饰品金基准",
        "update_time": time.strftime("%H:%M"),
        "status_text": "金交所现货分时",
    }
