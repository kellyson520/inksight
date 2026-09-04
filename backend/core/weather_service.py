"""
气象与天气预测服务 (Weather & Forecast Service)
整合 Open-Meteo 与 和风天气(QWeather)，提供穿衣出行建议与多日预报。
"""
from __future__ import annotations

import asyncio
import logging
import re
import time
import httpx
from datetime import datetime
from json import JSONDecodeError
from typing import Any

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from .config import (
    OPEN_METEO_URL,
    QWEATHER_API_KEY,
    QWEATHER_API_HOST,
    QWEATHER_PRIVATE_KEY,
    QWEATHER_CREDENTIAL_ID,
    QWEATHER_PROJECT_ID,
    _QWEATHER_ICON_TO_WMO,
    DEFAULT_LATITUDE,
    DEFAULT_LONGITUDE,
)
from .location_service import _resolve_city, extract_location_settings, _resolve_city_coords, _clean_location_text

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
async def _fetch_weather_data(url: str, params: dict) -> dict:
    """Fetch weather data with retry."""
    async with httpx.AsyncClient(timeout=5.0) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        return resp.json()


def _qweather_jwt() -> str | None:
    """Generate a short-lived JWT for QWeather Ed25519 auth."""
    if not (QWEATHER_PRIVATE_KEY and QWEATHER_CREDENTIAL_ID and QWEATHER_PROJECT_ID):
        return None
    try:
        import jwt as pyjwt
        import time
        now = int(time.time())
        payload = {"sub": QWEATHER_PROJECT_ID, "iat": now - 30, "exp": now + 900}
        headers = {"kid": QWEATHER_CREDENTIAL_ID}
        return pyjwt.encode(payload, QWEATHER_PRIVATE_KEY, algorithm="EdDSA", headers=headers)
    except Exception as e:
        logger.warning("[QWeather] JWT generation failed: %s", e)
        return None


def _qweather_has_credentials() -> bool:
    return bool(QWEATHER_API_KEY) or bool(QWEATHER_PRIVATE_KEY and QWEATHER_CREDENTIAL_ID and QWEATHER_PROJECT_ID)


def _qweather_auth_headers() -> dict[str, str]:
    """Build auth headers: prefer JWT over API KEY."""
    token = _qweather_jwt()
    if token:
        return {"Authorization": f"Bearer {token}"}
    if QWEATHER_API_KEY:
        return {"X-QW-Api-Key": QWEATHER_API_KEY}
    return {}


async def _qweather_get(path: str, params: dict) -> dict | None:
    """Call QWeather API. Returns parsed JSON on success, None on failure."""
    if not _qweather_has_credentials():
        return None
    url = f"https://{QWEATHER_API_HOST}{path}"
    headers = _qweather_auth_headers()
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(url, params=params, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            if str(data.get("code")) != "200":
                logger.warning("[QWeather] API returned code=%s for %s", data.get("code"), path)
                return None
            return data
    except (httpx.HTTPError, TypeError, ValueError, JSONDecodeError) as e:
        logger.warning("[QWeather] Failed to call %s: %s", path, e)
        return None


def _qweather_icon_to_wmo(icon_code: int | str) -> int:
    try:
        return _QWEATHER_ICON_TO_WMO.get(int(icon_code), -1)
    except (TypeError, ValueError):
        return -1


async def _qweather_current(lat: float, lon: float) -> dict | None:
    """Fallback: get current weather from QWeather."""
    location = f"{round(lon, 2)},{round(lat, 2)}"
    data = await _qweather_get("/v7/weather/now", {"location": location})
    if not data or "now" not in data:
        return None
    now = data["now"]
    try:
        temp = round(float(now.get("temp", 0)))
    except (TypeError, ValueError):
        temp = 0
    wmo = _qweather_icon_to_wmo(now.get("icon", -1))
    return {"temp": temp, "weather_code": wmo, "weather_str": f"{temp}°C"}


async def _qweather_forecast(lat: float, lon: float, days: int, language: str) -> dict | None:
    """Fallback: get forecast from QWeather."""
    location = f"{round(lon, 2)},{round(lat, 2)}"
    need = days + 1
    for tier in (3, 7, 10, 15, 30):
        if tier >= need:
            break
    day_key = f"{tier}d"
    lang_param = "en" if language == "en" else "zh"
    data = await _qweather_get(f"/v7/weather/{day_key}", {"location": location, "lang": lang_param})
    if not data or "daily" not in data:
        return None
    return data


async def get_weather(
    lat: float | None = None, lon: float | None = None, city: str | None = None
) -> dict:
    if lat is None or lon is None:
        lat, lon = await _resolve_city_coords(city)

    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,weather_code",
        "timezone": "auto",
    }
    try:
        data = await _fetch_weather_data(OPEN_METEO_URL, params)
        current = data["current"]
        return {
            "temp": round(current["temperature_2m"]),
            "weather_code": current["weather_code"],
            "weather_str": f"{round(current['temperature_2m'])}°C",
        }
    except (httpx.HTTPError, KeyError, TypeError, ValueError, Exception):
        logger.warning("[Context] Open-Meteo failed for city=%s, trying QWeather fallback", city)

    qw = await _qweather_current(lat, lon)
    if qw:
        logger.info("[Context] QWeather fallback succeeded for city=%s", city)
        return qw

    logger.warning("[Context] All weather sources failed for city=%s", city)
    return {"temp": 0, "weather_code": -1, "weather_str": "--°C"}


async def get_weather_cached(city: str | None = None, ttl: float = 1800) -> dict:
    """Cached version of get_weather (30min default TTL)."""
    cache_key = f"weather:{city or 'default'}"
    cached = _cache_get(cache_key, ttl)
    if cached is not None:
        return cached
    result = await get_weather(city=city)
    _cache_set(cache_key, result)
    return result


def _weather_code_to_desc(code: int, language: str = "zh") -> str:
    """Convert WMO weather code to localized description."""
    if language == "en":
        mapping = {
            0: "Sunny", 1: "Partly cloudy", 2: "Cloudy", 3: "Overcast",
            45: "Fog", 48: "Rime fog",
            51: "Light rain", 53: "Rain", 55: "Heavy rain",
            61: "Light rain", 63: "Rain", 65: "Heavy rain",
            71: "Light snow", 73: "Snow", 75: "Heavy snow",
            80: "Showers", 81: "Showers", 82: "Storm rain",
            95: "Thunderstorm", 96: "Thunderstorm", 99: "Thunderstorm",
        }
        return mapping.get(code, "Unknown")
    mapping = {
        0: "晴", 1: "多云", 2: "多云", 3: "阴",
        45: "雾", 48: "雾凇",
        51: "小雨", 53: "中雨", 55: "大雨",
        61: "小雨", 63: "中雨", 65: "大雨",
        71: "小雪", 73: "中雪", 75: "大雪",
        80: "阵雨", 81: "阵雨", 82: "暴雨",
        95: "雷阵雨", 96: "雷阵雨", 99: "雷阵雨",
    }
    return mapping.get(code, "未知")


def _safe_int(value: Any) -> int | None:
    try:
        if value in ("", None):
            return None
        return int(round(float(value)))
    except (TypeError, ValueError):
        return None


def _wind_level_number(wind_level: str) -> int | None:
    match = re.search(r"(\d+)", wind_level or "")
    if not match:
        return None
    try:
        return int(match.group(1))
    except (TypeError, ValueError):
        return None


def _generate_weather_advice(
    *,
    today_desc: str,
    today_low: str | int | None,
    today_high: str | int | None,
    today_humidity: str | int | None,
    today_wind_level: str,
    language: str = "zh",
) -> str:
    desc = _clean_location_text(today_desc, max_length=32)
    low = _safe_int(today_low)
    high = _safe_int(today_high)
    humidity = _safe_int(today_humidity)
    wind_level_num = _wind_level_number(today_wind_level)

    if language == "en":
        desc_lower = desc.lower()
        if "thunder" in desc_lower:
            return "Thunderstorms possible. Limit outdoor time."
        if "snow" in desc_lower:
            return "Snow and cold weather. Keep warm and watch your step."
        if "rain" in desc_lower or "shower" in desc_lower:
            return "Rain likely. Bring an umbrella and watch for slippery roads."
        if "fog" in desc_lower:
            return "Fog reduces visibility. Travel carefully."
        if high is not None and high >= 32:
            return "Hot weather. Stay hydrated and avoid strong sun."
        if low is not None and low <= 5:
            return "Cold outside. Dress warmly."
        if low is not None and high is not None and high - low >= 8:
            return "Big day-night temperature gap. Bring a light jacket."
        if wind_level_num is not None and wind_level_num >= 5:
            return "Windy conditions. Dress to block the wind."
        if humidity is not None and humidity >= 85:
            return "Very humid today. Dress light and stay comfortable."
        if high is not None and high >= 26:
            return "Warm weather. Light, breathable clothing works best."
        return "Comfortable weather for a light outfit."

    if "雷" in desc:
        return "有雷雨，尽量减少外出"
    if "雪" in desc:
        return "有雪天冷，注意保暖防滑"
    if "雨" in desc:
        return "有雨记得带伞，注意路滑"
    if "雾" in desc:
        return "有雾能见度低，出行留意"
    if high is not None and high >= 32:
        return "天气炎热，注意防晒补水"
    if low is not None and low <= 5:
        return "气温较低，外出注意保暖"
    if low is not None and high is not None and high - low >= 8:
        return "早晚温差大，记得带外套"
    if wind_level_num is not None and wind_level_num >= 5:
        return "风力较大，出门注意防风"
    if humidity is not None and humidity >= 85:
        return "空气潮湿，注意防潮添衣"
    if high is not None and high >= 26:
        return "气温偏高，穿着轻薄透气"
    return "气温适宜，轻装出行"


async def get_weather_forecast(
    city: str | None = None,
    days: int = 3,
    lat: float | None = None,
    lon: float | None = None,
    language: str = "zh",
) -> dict:
    """Get multi-day weather forecast from Open-Meteo."""
    # city 为空时，既要使用默认经纬度，也要在返回数据里给出一个可展示的城市名
    display_city = city or DEFAULT_CITY
    if language == "en" and display_city:
        try:
            localized = await _fetch_geocoding(display_city, count=1, language="en")
            results = localized.get("results") if isinstance(localized, dict) else None
            if isinstance(results, list) and results:
                parsed = _parse_geocoding_item(results[0])
                if parsed and parsed.get("city"):
                    display_city = str(parsed["city"])
        except (httpx.HTTPError, TypeError, ValueError, JSONDecodeError):
            logger.warning("[WeatherForecast] Failed to localize city name for %s", display_city, exc_info=True)
    if lat is None or lon is None:
        lat, lon = await _resolve_city_coords(display_city)
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": ",".join(
            [
                "temperature_2m",
                "weather_code",
                "relative_humidity_2m",
                "wind_direction_10m",
                "wind_speed_10m",
            ]
        ),
        # 预报字段：温度、天气代码、湿度、主导风向、风速、日出日落时间
        "daily": ",".join(
            [
                "temperature_2m_max",
                "temperature_2m_min",
                "weather_code",
                "relative_humidity_2m_mean",
                "winddirection_10m_dominant",
                "windspeed_10m_max",
                "sunrise",
                "sunset",
            ]
        ),
        "timezone": "auto",
        "forecast_days": days + 1,  # include today
    }
    try:
        forecast_url = (
            OPEN_METEO_URL.replace("/current", "/forecast")
            if "/current" in OPEN_METEO_URL
            else OPEN_METEO_URL
        )
        data = await _fetch_weather_data(forecast_url, params)
        current = data.get("current", {}) if isinstance(data.get("current"), dict) else {}
        daily = data.get("daily", {})
        dates = daily.get("time", [])
        t_max = daily.get("temperature_2m_max", [])
        t_min = daily.get("temperature_2m_min", [])
        codes = daily.get("weather_code", [])
        humidities = daily.get("relative_humidity_2m_mean", [])
        wind_dirs = daily.get("winddirection_10m_dominant", [])
        wind_speeds = daily.get("windspeed_10m_max", [])
        sunrises = daily.get("sunrise", [])
        sunsets = daily.get("sunset", [])

        weekday_short = (
            ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
            if language == "en"
            else ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        )
        now = datetime.now()
        today_date = now.date()
        
        # 构建完整的预报列表，包括昨天、今天、明天、后天等
        full_forecast = []
        for i in range(min(len(dates), days + 1)):
            d = datetime.strptime(dates[i], "%Y-%m-%d")
            date_obj = d.date()
            date_str = d.strftime("%m/%d")
            
            # 判断是昨天、今天、明天还是其他
            delta = (date_obj - today_date).days
            if delta == -1:
                day_label = "Yesterday" if language == "en" else "昨天"
            elif delta == 0:
                day_label = "Today" if language == "en" else "今天"
            elif delta == 1:
                day_label = "Tomorrow" if language == "en" else "明天"
            else:
                day_label = weekday_short[d.weekday()]
            
            wcode = codes[i] if i < len(codes) else -1
            desc = _weather_code_to_desc(wcode, language=language)
            
            temp_min = round(t_min[i]) if i < len(t_min) else None
            temp_max = round(t_max[i]) if i < len(t_max) else None
            
            if temp_min is not None and temp_max is not None:
                temp_range = f"{temp_min}° / {temp_max}°" if language == "en" else f"{temp_min}℃ / {temp_max}℃"
            else:
                temp_range = "--"
            
            full_forecast.append(
                {
                    "day": day_label,
                    "date": date_str,
                    "temp_range": temp_range,
                    "temp_min": str(temp_min) if temp_min is not None else "--",
                    "temp_max": str(temp_max) if temp_max is not None else "--",
                    "desc": desc,
                    "code": wcode,
                }
            )

        # 今天的天气信息
        today = full_forecast[0] if full_forecast else {}
        today_high = today.get("temp_max", "--")
        today_low = today.get("temp_min", "--")
        current_temp = _safe_int(current.get("temperature_2m"))
        current_code = _safe_int(current.get("weather_code"))
        today_temp = str(current_temp) if current_temp is not None else today_high
        today_code = current_code if current_code is not None else today.get("code", -1)
        today_desc = _weather_code_to_desc(today_code, language=language)

        if today_low != "--" and today_high != "--":
            today_range = f"{today_low}°C / {today_high}°C"
        else:
            today_range = "-- / --"

        # 今天的湿度
        today_humidity = "--"
        current_humidity = _safe_int(current.get("relative_humidity_2m"))
        if current_humidity is not None:
            today_humidity = str(current_humidity)
        elif humidities:
            try:
                today_humidity = str(int(round(humidities[0])))
            except (TypeError, ValueError):
                today_humidity = "--"

        # 今天的风向和风力（等级粗略按风速估计）
        def _deg_to_wind_dir(deg: float) -> str:
            dirs = (
                ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
                if language == "en"
                else ["北风", "东北风", "东风", "东南风", "南风", "西南风", "西风", "西北风"]
            )
            try:
                idx = int((deg % 360) / 45 + 0.5) % 8
                return dirs[idx]
            except (TypeError, ValueError):
                logger.warning("[Context] Invalid wind direction value: %s", deg, exc_info=True)
                return ""

        today_wind_dir = ""
        current_wind_dir = current.get("wind_direction_10m")
        if current_wind_dir is not None:
            try:
                today_wind_dir = _deg_to_wind_dir(float(current_wind_dir))
            except (TypeError, ValueError):
                today_wind_dir = ""
        elif wind_dirs:
            try:
                today_wind_dir = _deg_to_wind_dir(float(wind_dirs[0]))
            except (TypeError, ValueError):
                today_wind_dir = ""

        today_wind_level = ""
        current_wind_speed = current.get("wind_speed_10m")
        wind_speed_for_level = current_wind_speed if current_wind_speed is not None else (wind_speeds[0] if wind_speeds else None)
        if wind_speed_for_level is not None:
            try:
                # 这里使用风速近似为等级（粗略）：m/s 四舍五入作为“几级”
                level = max(1, min(12, int(round(float(wind_speed_for_level) / 2))))  # 简单映射
                today_wind_level = f"Lv {level}" if language == "en" else f"{level}级"
            except (TypeError, ValueError):
                today_wind_level = ""

        advice = _generate_weather_advice(
            today_desc=today_desc,
            today_low=today_low,
            today_high=today_high,
            today_humidity=today_humidity,
            today_wind_level=today_wind_level,
            language=language,
        )

        # 日出日落时间（取今天）
        sunrise_str = ""
        sunset_str = ""
        if sunrises:
            try:
                sr = datetime.fromisoformat(sunrises[0])
                sunrise_str = sr.strftime("%H:%M")
            except (TypeError, ValueError):
                logger.warning("[Context] Failed to parse sunrise value: %s", sunrises[0], exc_info=True)
                sunrise_str = ""
        if sunsets:
            try:
                ss = datetime.fromisoformat(sunsets[0])
                sunset_str = ss.strftime("%H:%M")
            except (TypeError, ValueError):
                logger.warning("[Context] Failed to parse sunset value: %s", sunsets[0], exc_info=True)
                sunset_str = ""

        return {
            "city": display_city,
            "today_temp": today_temp,
            "today_desc": today_desc,
            "today_code": today_code,
            "today_low": today_low,
            "today_high": today_high,
            "today_range": today_range,
            "today_humidity": today_humidity,
            "today_wind_dir": today_wind_dir,
            "today_wind_level": today_wind_level,
            "sunrise": sunrise_str,
            "sunset": sunset_str,
            "advice": advice,
            # 仅返回“未来 4 天”的预报（不含今天）
            "forecast": full_forecast[1 : days + 1] if len(full_forecast) > 1 else [],
        }
    except (httpx.HTTPError, KeyError, TypeError, ValueError, JSONDecodeError) as e:
        logger.warning("[WeatherForecast] Open-Meteo failed (%s), trying QWeather fallback", e)

    qw_result = await _qweather_forecast_to_standard(lat, lon, days, display_city, language)
    if qw_result:
        logger.info("[WeatherForecast] QWeather fallback succeeded for city=%s", display_city)
        return qw_result

    logger.warning("[WeatherForecast] All weather sources failed for city=%s", display_city)
    return {
        "city": city or DEFAULT_CITY,
        "today_temp": "--",
        "today_desc": "No data" if language == "en" else "暂无数据",
        "today_code": -1,
        "today_low": "--",
        "today_high": "--",
        "today_range": "-- / --",
        "advice": "Dress for the weather." if language == "en" else "注意根据天气添减衣物",
        "forecast": [],
    }


async def _qweather_forecast_to_standard(
    lat: float, lon: float, days: int, display_city: str, language: str
) -> dict | None:
    """Convert QWeather forecast response to the same dict shape as Open-Meteo path."""
    data = await _qweather_forecast(lat, lon, days, language)
    if not data:
        return None
    daily_list = data.get("daily", [])
    if not daily_list:
        return None

    weekday_short = (
        ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        if language == "en"
        else ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    )
    today_date = datetime.now().date()

    full_forecast: list[dict] = []
    for item in daily_list:
        try:
            d = datetime.strptime(item.get("fxDate", ""), "%Y-%m-%d")
        except (TypeError, ValueError):
            continue
        date_obj = d.date()
        date_str = d.strftime("%m/%d")
        delta = (date_obj - today_date).days
        if delta == -1:
            day_label = "Yesterday" if language == "en" else "昨天"
        elif delta == 0:
            day_label = "Today" if language == "en" else "今天"
        elif delta == 1:
            day_label = "Tomorrow" if language == "en" else "明天"
        else:
            day_label = weekday_short[d.weekday()]

        wmo = _qweather_icon_to_wmo(item.get("iconDay", -1))
        desc = item.get("textDay", "") or _weather_code_to_desc(wmo, language=language)
        try:
            temp_min = round(float(item.get("tempMin", 0)))
            temp_max = round(float(item.get("tempMax", 0)))
        except (TypeError, ValueError):
            temp_min, temp_max = 0, 0
        temp_range = (
            f"{temp_min}° / {temp_max}°" if language == "en" else f"{temp_min}℃ / {temp_max}℃"
        )
        full_forecast.append({
            "day": day_label,
            "date": date_str,
            "temp_range": temp_range,
            "temp_min": str(temp_min),
            "temp_max": str(temp_max),
            "desc": desc,
            "code": wmo,
        })

    if not full_forecast:
        return None

    today = full_forecast[0]
    today_high = today.get("temp_max", "--")
    today_low = today.get("temp_min", "--")
    today_desc = today.get("desc", "")
    today_code = today.get("code", -1)
    today_range = f"{today_low}°C / {today_high}°C" if today_low != "--" else "-- / --"

    first_item = daily_list[0] if daily_list else {}
    today_humidity = str(first_item.get("humidity", "--"))
    today_wind_dir = str(first_item.get("windDirDay", ""))
    today_wind_level = str(first_item.get("windScaleDay", ""))
    if today_wind_level and today_wind_level != "--":
        today_wind_level = f"Lv {today_wind_level}" if language == "en" else f"{today_wind_level}级"

    advice = _generate_weather_advice(
        today_desc=today_desc,
        today_low=today_low,
        today_high=today_high,
        today_humidity=today_humidity,
        today_wind_level=today_wind_level,
        language=language,
    )

    return {
        "city": display_city,
        "today_temp": today_high,
        "today_desc": today_desc,
        "today_code": today_code,
        "today_low": today_low,
        "today_high": today_high,
        "today_range": today_range,
        "today_humidity": today_humidity,
        "today_wind_dir": today_wind_dir,
        "today_wind_level": today_wind_level,
        "sunrise": "",
        "sunset": "",
        "advice": advice,
        "forecast": full_forecast[1 : days + 1] if len(full_forecast) > 1 else [],
    }

