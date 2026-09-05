"""
系统上下文与环境聚合门面 (Context Aggregator & Facade)
负责日期节日上下文、节假日预测、电池电量估算，并统一重导出地理位置与天气服务。
"""
from __future__ import annotations

import asyncio
import logging
import random
import time
import httpx
from datetime import datetime
from urllib.parse import urlencode
from json import JSONDecodeError
from typing import Any

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)
from zhdate import ZhDate

from .config import (
    WEEKDAY_CN,
    MONTH_CN,
    SOLAR_FESTIVALS,
    LUNAR_FESTIVALS,
    IDIOMS,
    POEMS,
    HOLIDAY_WORK_API_URL,
    HOLIDAY_NEXT_API_URL,
    QWEATHER_API_KEY,
    QWEATHER_API_HOST,
)

import sys
from . import location_service as _loc_mod
from . import weather_service as _wx_mod
from .outbound_http import RequestPolicy, outbound_http

# 统一重导出地理位置与气象服务，保持 100% 向后兼容
from .location_service import (
    LocationSearchScope,
    search_locations,
    extract_location_settings,
    _resolve_city,
    _normalize_place_name,
    _clean_location_text,
    _clean_float,
    _fetch_nominatim,
    _fetch_geocoding,
)
from .weather_service import (
    get_weather,
    get_weather_cached,
    get_weather_forecast,
    _generate_weather_advice,
    _weather_code_to_desc,
    _qweather_current,
    _qweather_forecast_to_standard,
    _qweather_icon_to_wmo,
    _fetch_weather_data,
)

class _ContextModule(sys.modules[__name__].__class__):
    def __setattr__(self, name, value):
        super().__setattr__(name, value)
        for mod in (_loc_mod, _wx_mod):
            if hasattr(mod, name):
                setattr(mod, name, value)

sys.modules[__name__].__class__ = _ContextModule

logger = logging.getLogger(__name__)

_context_cache: dict[str, tuple[Any, float]] = {}

_api_retry = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=5),
    retry=retry_if_exception_type((
        httpx.ConnectError,
        httpx.ReadTimeout,
        httpx.ConnectTimeout,
    )),
    reraise=True,
)

def _cache_get(key: str, ttl: float) -> Any | None:
    if key in _context_cache:
        val, ts = _context_cache[key]
        if time.time() - ts < ttl:
            return val
        del _context_cache[key]
    return None

def _cache_set(key: str, val: Any):
    _context_cache[key] = (val, time.time())

@_api_retry
async def _fetch_holiday_info(date_str: str) -> dict:
    """Fetch holiday info with retry."""
    url = f"{HOLIDAY_WORK_API_URL}?{urlencode({'date': date_str})}"
    response = await asyncio.to_thread(
        outbound_http.get_json,
        url,
        policy=RequestPolicy(timeout=httpx.Timeout(3.0), max_attempts=1),
    )
    return response.json()


async def get_holiday_info(date: datetime) -> dict:
    date_str = date.strftime("%Y-%m-%d")
    try:
        result = await _fetch_holiday_info(date_str)
        if result.get("code") == 200 and result.get("data"):
            data = result["data"]
            is_work = data.get("work", True)
            return {
                    "is_holiday": not is_work,
                    "holiday_name": "",
                    "is_workday": is_work,
                }
        else:
            return {"is_holiday": False, "holiday_name": "", "is_workday": False}
    except (httpx.HTTPError, JSONDecodeError, TypeError, ValueError):
        logger.warning("[Context] Failed to fetch holiday info for %s", date_str, exc_info=True)
        return {"is_holiday": False, "holiday_name": "", "is_workday": False}


@_api_retry
async def _fetch_upcoming_holiday() -> dict:
    """Fetch upcoming holiday info with retry."""
    response = await asyncio.to_thread(
        outbound_http.get_json,
        HOLIDAY_NEXT_API_URL,
        policy=RequestPolicy(timeout=httpx.Timeout(3.0), max_attempts=1),
    )
    return response.json()


async def get_upcoming_holiday(now: datetime) -> dict:
    try:
        result = await _fetch_upcoming_holiday()
        if result.get("code") == 200 and result.get("data"):
            data = result["data"]
            holiday_date_str = data.get("date", "")

            if holiday_date_str:
                from datetime import datetime as dt

                holiday_date = dt.strptime(holiday_date_str, "%Y-%m-%d")
                days_until = (holiday_date.date() - now.date()).days

                return {
                    "days_until": days_until if days_until > 0 else 0,
                    "holiday_name": data.get("name", ""),
                    "date": holiday_date.strftime("%m月%d日"),
                    "holiday_duration": data.get("days", 0),
                }
    except (httpx.HTTPError, JSONDecodeError, TypeError, ValueError):
        logger.warning("[Context] Failed to fetch upcoming holiday", exc_info=True)

    return {"days_until": 0, "holiday_name": "", "date": "", "holiday_duration": 0}


async def get_date_context() -> dict:
    now = datetime.now()
    day_of_year = now.timetuple().tm_yday
    days_in_year = (
        366
        if (now.year % 4 == 0 and (now.year % 100 != 0 or now.year % 400 == 0))
        else 365
    )
    
    festival = SOLAR_FESTIVALS.get((now.month, now.day), "")
    
    try:
        lunar = ZhDate.from_datetime(now)
        lunar_festival = LUNAR_FESTIVALS.get((lunar.lunar_month, lunar.lunar_day), "")
        if lunar_festival and not festival:
            festival = lunar_festival
    except ValueError:
        logger.warning("[Context] Failed to resolve lunar date for %s", now.isoformat(), exc_info=True)
    
    holiday_info = await get_holiday_info(now)
    if holiday_info["holiday_name"] and not festival:
        festival = holiday_info["holiday_name"]
    
    upcoming = await get_upcoming_holiday(now)
    
    daily_word = random.choice(IDIOMS + POEMS)
    
    return {
        "date_str": f"{now.month}月{now.day}日 {WEEKDAY_CN[now.weekday()]}",
        "time_str": f"{now.hour:02d}:{now.minute:02d}:{now.second:02d}",
        "weekday": now.weekday(),
        "hour": now.hour,
        "is_weekend": now.weekday() >= 5,
        "year": now.year,
        "day": now.day,
        "month_cn": MONTH_CN[now.month - 1],
        "weekday_cn": WEEKDAY_CN[now.weekday()],
        "day_of_year": day_of_year,
        "days_in_year": days_in_year,
        "festival": festival,
        "is_holiday": holiday_info["is_holiday"],
        "is_workday": holiday_info["is_workday"],
        "upcoming_holiday": upcoming["holiday_name"],
        "days_until_holiday": upcoming["days_until"],
        "holiday_date": upcoming["date"],
        "daily_word": daily_word,
    }


async def get_date_context_cached(ttl: float = 900) -> dict:
    """Cached version of get_date_context (15min default TTL)."""
    cached = _cache_get("date_context", ttl)
    if cached is not None:
        return cached
    result = await get_date_context()
    _cache_set("date_context", result)
    return result


def calc_battery_pct(voltage: float) -> int:
    """
    两段式折线估算锂电池电量百分比。

    锂离子电池电压-电量曲线是非线性的：
    - 高电量区间 (3.70V~4.20V)：电压变化快，电量变化慢
    - 低电量区间 (3.00V~3.70V)：电压变化慢，电量变化快
    """
    V_FULL = 4.20   # 满电电压
    V_HIGH = 3.70   # 高电量阈值
    V_LOW = 3.00    # 过放保护阈值

    if voltage >= V_HIGH:
        pct = (voltage - V_HIGH) / (V_FULL - V_HIGH) * 50 + 50
    else:
        pct = (voltage - V_LOW) / (V_HIGH - V_LOW) * 50

    if pct > 100:
        pct = 100
    elif pct < 0:
        pct = 0

    return int(pct)


def choose_persona(weekday: int, hour: int) -> str:
    import random

    return random.choice(["STOIC", "ROAST", "ZEN", "DAILY"])
