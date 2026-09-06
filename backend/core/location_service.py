"""
地理编码与位置检索服务 (Location & Geocoding Service)
提供内置城市库匹配、Nominatim 与 Open-Meteo 搜索及位置反解。
"""
from __future__ import annotations

import asyncio
import logging
import re
import time
import httpx
from json import JSONDecodeError
from typing import Any, Literal
from urllib.parse import urlencode

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from .outbound_http import RequestPolicy, outbound_http
from .config import (
    CITY_COORDINATES,
    DEFAULT_LATITUDE,
    DEFAULT_LONGITUDE,
    OPEN_METEO_GEOCODING_URL,
    DEFAULT_CITY,
)

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
_NOMINATIM_SEARCH_URL = "https://nominatim.openstreetmap.org/search"
_NOMINATIM_USER_AGENT = "InkSight/1.0 (weather location search)"
_CN_TIMEZONE = "Asia/Shanghai"
_CN_SEARCH_COUNTRY_CODE = "cn"
_NOMINATIM_QUERY_SUFFIXES = ("市", "县", "区")
_NOMINATIM_ADMIN_TYPES = {
    "administrative",
    "city",
    "county",
    "district",
    "municipality",
    "province",
    "region",
    "state",
    "suburb",
    "town",
    "village",
}
_NOMINATIM_POI_CATEGORIES = {
    "aerialway",
    "aeroway",
    "amenity",
    "building",
    "highway",
    "historic",
    "landuse",
    "leisure",
    "man_made",
    "office",
    "railway",
    "shop",
    "tourism",
}
_NOMINATIM_POI_TYPES = {
    "bus_stop",
    "halt",
    "platform",
    "station",
    "tram_stop",
}
LocationSearchScope = Literal["auto", "cn", "global"]

_LOCATION_SUFFIXES = (
    "特别行政区",
    "自治区",
    "自治州",
    "自治县",
    "地区",
    "盟",
    "省",
    "市",
    "区",
    "县",
)

# Reusable retry decorator for external API calls
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


def _normalize_place_name(name: str | None) -> str:
    if not isinstance(name, str):
        return ""
    normalized = name.strip().replace(" ", "")
    for token in ("中国", "中华人民共和国"):
        if normalized.startswith(token):
            normalized = normalized[len(token):]
    normalized = normalized.strip("·,-_/，、 ")
    for suffix in _LOCATION_SUFFIXES:
        if normalized.endswith(suffix) and len(normalized) > len(suffix):
            normalized = normalized[: -len(suffix)]
            break
    return normalized


def _clean_location_text(value: Any, max_length: int = 64) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip()[:max_length]


def _clean_float(value: Any) -> float | None:
    try:
        if value in ("", None):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def extract_location_settings(config: dict | None, *, fallback_city: str | None = None) -> dict[str, Any]:
    if not isinstance(config, dict):
        return {"city": fallback_city} if fallback_city else {}

    city = _clean_location_text(config.get("city"), max_length=40)
    latitude = _clean_float(config.get("latitude"))
    longitude = _clean_float(config.get("longitude"))

    location: dict[str, Any] = {}
    if city:
        location["city"] = city
    elif fallback_city:
        location["city"] = fallback_city
    if latitude is not None and longitude is not None:
        location["lat"] = latitude
        location["lon"] = longitude
    return location


def _resolve_city(city: str | None) -> tuple[float, float]:
    if not city:
        return DEFAULT_LATITUDE, DEFAULT_LONGITUDE
    coords = CITY_COORDINATES.get(city)
    if coords:
        return coords
    normalized = _normalize_place_name(city)
    for name, c in CITY_COORDINATES.items():
        if _normalize_place_name(name) == normalized:
            return c
    return DEFAULT_LATITUDE, DEFAULT_LONGITUDE


@_api_retry
async def _fetch_geocoding(
    name: str,
    *,
    count: int = 1,
    country_code: str | None = None,
    language: str = "zh",
) -> dict:
    params = {
        "name": name,
        "count": count,
        "language": "en" if language == "en" else "zh",
        "format": "json",
    }
    if country_code:
        params["countryCode"] = country_code
    query = urlencode(params)
    response = await asyncio.to_thread(
        outbound_http.get_json,
        f"{OPEN_METEO_GEOCODING_URL}?{query}",
        policy=RequestPolicy(max_attempts=1, follow_redirects=False),
    )
    return response.json()


def _format_location_label(name: str, admin1: str = "", country: str = "") -> str:
    parts = [part for part in (name, admin1, country) if part]
    return " · ".join(parts)


def _contains_cjk(text: str) -> bool:
    return any("\u4e00" <= ch <= "\u9fff" for ch in text)


def _contains_latin_letters(text: str) -> bool:
    return any(ch.isascii() and ch.isalpha() for ch in text)


def _looks_like_china_country(country: str) -> bool:
    normalized = _clean_location_text(country, max_length=80)
    return "中国" in normalized or "中國" in normalized or normalized.lower() in {"china", "cn"}


def _search_country_code_sequence(query: str, scope: LocationSearchScope) -> list[str | None]:
    if scope == "cn":
        return [_CN_SEARCH_COUNTRY_CODE]
    if scope == "global":
        return [None]
    if _contains_latin_letters(query):
        return [None, _CN_SEARCH_COUNTRY_CODE]
    return [_CN_SEARCH_COUNTRY_CODE, None]


def _build_location_queries(query: str) -> list[str]:
    query = _clean_location_text(query, max_length=60)
    normalized = _normalize_place_name(query)
    if not query:
        return []

    variants: list[str] = [query]
    if normalized and normalized != query:
        variants.append(normalized)

    if normalized and _contains_cjk(normalized):
        has_suffix = any(query.endswith(suffix) for suffix in _LOCATION_SUFFIXES)
        if not has_suffix:
            for suffix in _NOMINATIM_QUERY_SUFFIXES:
                variants.append(f"{normalized}{suffix}")

    deduped: list[str] = []
    seen: set[str] = set()
    for item in variants:
        cleaned = _clean_location_text(item, max_length=60)
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            deduped.append(cleaned)
    return deduped[:4]


def _builtin_location_items(query: str, limit: int, locale: str = "zh") -> list[dict]:
    if locale == "en":
        return []
    normalized_query = _normalize_place_name(query)
    if not normalized_query:
        return []

    results: list[dict] = []
    for name, (lat, lon) in CITY_COORDINATES.items():
        normalized_name = _normalize_place_name(name)
        if normalized_query not in normalized_name:
            continue
        results.append(
            {
                "city": name,
                "display_name": name,
                "admin1": "",
                "country": "",
                "latitude": lat,
                "longitude": lon,
                "timezone": "Asia/Shanghai",
                "_score": 100 if normalized_name == normalized_query else 80,
            }
        )

    results.sort(key=lambda item: (-int(item.get("_score", 0)), item.get("city", "")))
    return results[:limit]


def _parse_geocoding_item(item: dict) -> dict | None:
    if not isinstance(item, dict):
        return None
    name = _clean_location_text(item.get("name"), max_length=40)
    if not name:
        return None

    latitude = _clean_float(item.get("latitude"))
    longitude = _clean_float(item.get("longitude"))
    if latitude is None or longitude is None:
        return None

    admin1 = _clean_location_text(item.get("admin1"))
    country = _clean_location_text(item.get("country"))
    timezone = _clean_location_text(item.get("timezone")) or "Asia/Shanghai"
    population = 0
    try:
        population = int(item.get("population") or 0)
    except (TypeError, ValueError):
        population = 0

    aliases: list[str] = []
    for value in (
        item.get("name"),
        item.get("admin2"),
        item.get("admin3"),
        item.get("admin4"),
    ):
        alias = _clean_location_text(value, max_length=80)
        if alias and alias not in aliases:
            aliases.append(alias)

    return {
        "city": name,
        "display_name": _format_location_label(name, admin1, country),
        "admin1": admin1,
        "country": country,
        "latitude": latitude,
        "longitude": longitude,
        "timezone": timezone,
        "_score": population,
        "_aliases": aliases,
    }


@_api_retry
async def _fetch_nominatim(
    query: str,
    *,
    count: int = 8,
    country_codes: str | None = _CN_SEARCH_COUNTRY_CODE,
    locale: str = "zh",
) -> list[dict]:
    params = {
        "q": query,
        "format": "jsonv2",
        "addressdetails": 1,
        "accept-language": "en-US,en" if locale == "en" else "zh-CN",
        "limit": count,
    }
    if country_codes:
        params["countrycodes"] = country_codes

    response = await asyncio.to_thread(
        outbound_http.get_json,
        f"{_NOMINATIM_SEARCH_URL}?{urlencode(params)}",
        headers={"User-Agent": _NOMINATIM_USER_AGENT},
        policy=RequestPolicy(timeout=5.0, max_attempts=1, follow_redirects=False),
    )
    data = response.json()
    return data if isinstance(data, list) else []


def _pick_first_text(values: list[Any], *, max_length: int = 40) -> str:
    for value in values:
        cleaned = _clean_location_text(value, max_length=max_length)
        if cleaned:
            return cleaned
    return ""


def _normalize_match_text(text: str) -> str:
    cleaned = _clean_location_text(text, max_length=160).lower()
    return re.sub(r"[\s·,.;:，。；：/()（）\-_]+", " ", cleaned).strip()


def _location_matches_query(item: dict, query: str) -> bool:
    normalized_query = _normalize_place_name(query)
    if not normalized_query:
        return True

    candidates = [
        _clean_location_text(str(item.get("city", "")), max_length=80),
        _clean_location_text(str(item.get("display_name", "")), max_length=160),
    ]
    aliases = item.get("_aliases")
    if isinstance(aliases, list):
        candidates.extend(
            _clean_location_text(str(alias), max_length=80)
            for alias in aliases
            if alias
        )

    if _contains_cjk(normalized_query):
        return any(
            normalized_query in _normalize_place_name(candidate)
            for candidate in candidates
            if candidate
        )

    normalized_candidates = [_normalize_match_text(candidate) for candidate in candidates if candidate]
    normalized_query_text = _normalize_match_text(query)
    if not normalized_query_text:
        return True

    query_tokens = [token for token in normalized_query_text.split(" ") if token]
    if not query_tokens:
        return any(normalized_query_text in candidate for candidate in normalized_candidates)

    for candidate in normalized_candidates:
        candidate_tokens = [token for token in candidate.split(" ") if token]
        if not candidate_tokens:
            continue
        if all(any(token == candidate_token or candidate_token.startswith(token) for candidate_token in candidate_tokens) for token in query_tokens):
            return True
    return False


def _is_poi_like(item: dict) -> bool:
    category = _clean_location_text(str(item.get("_category", "")), max_length=32).lower()
    addresstype = _clean_location_text(str(item.get("_addresstype", "")), max_length=32).lower()
    item_type = _clean_location_text(str(item.get("_item_type", "")), max_length=32).lower()
    city = _clean_location_text(str(item.get("city", "")), max_length=80)

    if category in _NOMINATIM_POI_CATEGORIES:
        return True
    if addresstype in _NOMINATIM_POI_TYPES or item_type in _NOMINATIM_POI_TYPES:
        return True
    return any(token in city for token in ("机场", "大桥", "公司", "配餐部", "食品有限公司"))


def _is_admin_like(item: dict) -> bool:
    category = _clean_location_text(str(item.get("_category", "")), max_length=32).lower()
    addresstype = _clean_location_text(str(item.get("_addresstype", "")), max_length=32).lower()
    item_type = _clean_location_text(str(item.get("_item_type", "")), max_length=32).lower()
    city = _clean_location_text(str(item.get("city", "")), max_length=80)

    if category == "boundary" and item_type == "administrative":
        return True
    if addresstype in _NOMINATIM_ADMIN_TYPES or item_type in _NOMINATIM_ADMIN_TYPES:
        return True
    return city.endswith(("市", "区", "县", "镇", "州", "省"))


def _location_starts_with_query(item: dict, query: str) -> bool:
    normalized_query = _normalize_place_name(query)
    city = _normalize_place_name(str(item.get("city", "")))
    return bool(normalized_query and city.startswith(normalized_query))


def _refine_location_items(items: list[dict], query: str) -> list[dict]:
    matched = [item for item in items if _location_matches_query(item, query)]
    normalized_query = _normalize_place_name(query)
    if not normalized_query or not _contains_cjk(normalized_query):
        return matched

    has_admin_anchor = any(
        _is_admin_like(item) and _location_starts_with_query(item, query)
        for item in matched
    )
    if not has_admin_anchor:
        return matched

    refined = [item for item in matched if not _is_poi_like(item)]
    return refined or matched


def _extract_nominatim_name(item: dict) -> str:
    address = item.get("address") if isinstance(item.get("address"), dict) else {}
    return _pick_first_text(
        [
            item.get("name"),
            address.get("city"),
            address.get("county"),
            address.get("district"),
            address.get("town"),
            address.get("municipality"),
            address.get("state_district"),
            address.get("province"),
            address.get("state"),
            address.get("village"),
            address.get("hamlet"),
        ]
    )


def _nominatim_timezone(item: dict) -> str:
    address = item.get("address") if isinstance(item.get("address"), dict) else {}
    country_code = _clean_location_text(address.get("country_code"), max_length=8).lower()
    if country_code == "cn":
        return _CN_TIMEZONE
    return _clean_location_text(item.get("timezone"), max_length=64)


def _score_nominatim_item(item: dict, query: str) -> int:
    normalized_query = _normalize_place_name(query)
    best_name = _extract_nominatim_name(item)
    normalized_name = _normalize_place_name(best_name)
    display_name = _normalize_place_name(_clean_location_text(item.get("display_name"), max_length=160))
    addresstype = _clean_location_text(item.get("addresstype"), max_length=32).lower()
    category = _clean_location_text(item.get("category"), max_length=32).lower()
    item_type = _clean_location_text(item.get("type"), max_length=32).lower()

    score = 0

    try:
        score += int(float(item.get("importance") or 0) * 1000)
    except (TypeError, ValueError):
        pass

    try:
        score += int(item.get("place_rank") or 0)
    except (TypeError, ValueError):
        pass

    if normalized_query and normalized_name == normalized_query:
        score += 1200
    elif normalized_query and normalized_query in normalized_name:
        score += 800
    elif normalized_query and normalized_query in display_name:
        score += 500

    if category == "boundary" and item_type == "administrative":
        score += 900
    if category == "place":
        score += 550
    if addresstype in _NOMINATIM_ADMIN_TYPES:
        score += 450
    if item_type in _NOMINATIM_ADMIN_TYPES:
        score += 220

    if category in _NOMINATIM_POI_CATEGORIES:
        score -= 800
    if addresstype in _NOMINATIM_POI_TYPES:
        score -= 800
    if item_type in _NOMINATIM_POI_TYPES:
        score -= 900

    return score


def _parse_nominatim_item(item: dict, query: str) -> dict | None:
    if not isinstance(item, dict):
        return None

    latitude = _clean_float(item.get("lat"))
    longitude = _clean_float(item.get("lon"))
    if latitude is None or longitude is None:
        return None

    address = item.get("address") if isinstance(item.get("address"), dict) else {}
    city = _extract_nominatim_name(item)
    if not city:
        return None

    admin2 = _pick_first_text(
        [
            address.get("city"),
            address.get("municipality"),
            address.get("state_district"),
            address.get("county"),
            address.get("district"),
        ]
    )
    admin1 = _pick_first_text([address.get("state"), address.get("province")])
    country = _pick_first_text([address.get("country")])

    display_parts: list[str] = [city]
    if admin2 and admin2 != city:
        display_parts.append(admin2)
    if admin1 and admin1 not in display_parts:
        display_parts.append(admin1)
    if country and country not in display_parts:
        display_parts.append(country)

    return {
        "city": city,
        "display_name": " · ".join(display_parts),
        "admin1": admin1,
        "country": country,
        "latitude": latitude,
        "longitude": longitude,
        "timezone": _nominatim_timezone(item),
        "_score": _score_nominatim_item(item, query),
        "_category": _clean_location_text(item.get("category"), max_length=32).lower(),
        "_addresstype": _clean_location_text(item.get("addresstype"), max_length=32).lower(),
        "_item_type": _clean_location_text(item.get("type"), max_length=32).lower(),
    }


async def _search_nominatim_locations(
    query: str,
    limit: int,
    *,
    scope: LocationSearchScope = "auto",
    locale: str = "zh",
) -> list[dict]:
    variants = _build_location_queries(query)
    if not variants:
        return []

    count = max(limit * 2, 6)
    results: list[dict] = []
    country_sequences = _search_country_code_sequence(query, scope)

    async def _fetch_variant(variant: str, country_codes: str | None) -> list[dict]:
        try:
            return await _fetch_nominatim(
                variant,
                count=count,
                country_codes=country_codes,
                locale=locale,
            )
        except (httpx.HTTPError, TypeError, ValueError, JSONDecodeError):
            logger.warning(
                "[Context] Failed to search Nominatim for query=%s variant=%s",
                query,
                variant,
                exc_info=True,
            )
            return []

    for country_codes in country_sequences:
        batches = await asyncio.gather(
            *[_fetch_variant(variant, country_codes) for variant in variants]
        )
        for variant, batch in zip(variants, batches):
            for item in batch:
                parsed = _parse_nominatim_item(item, variant)
                if not parsed:
                    continue
                if country_codes == _CN_SEARCH_COUNTRY_CODE and scope != "global":
                    parsed["_score"] = int(parsed.get("_score", 0)) + 150
                results.append(parsed)
    return results


def _dedupe_location_items(items: list[dict], limit: int) -> list[dict]:
    deduped: list[dict] = []
    seen: set[tuple[Any, ...]] = set()
    seen_labels: set[str] = set()
    sorted_items = sorted(
        items,
        key=lambda item: (
            -int(item.get("_score", 0)),
            item.get("country", ""),
            item.get("admin1", ""),
            item.get("city", ""),
        ),
    )
    for item in sorted_items:
        display_name = _clean_location_text(item.get("display_name"), max_length=160)
        label_key = _normalize_place_name(display_name or item.get("city", ""))
        if label_key and label_key in seen_labels:
            continue
        key = (
            item.get("city", ""),
            item.get("admin1", ""),
            item.get("country", ""),
            round(float(item.get("latitude", 0.0)), 4),
            round(float(item.get("longitude", 0.0)), 4),
        )
        if key in seen:
            continue
        if label_key:
            seen_labels.add(label_key)
        seen.add(key)
        cleaned = {k: v for k, v in item.items() if not k.startswith("_")}
        deduped.append(cleaned)
        if len(deduped) >= limit:
            break
    return deduped


async def search_locations(
    query: str,
    limit: int = 8,
    scope: LocationSearchScope = "auto",
    locale: str = "zh",
) -> list[dict]:
    query = _clean_location_text(query, max_length=60)
    if not query:
        return []

    if scope not in {"auto", "cn", "global"}:
        scope = "auto"

    locale = "en" if locale == "en" else "zh"
    cache_key = f"location-search:{query}:{limit}:{scope}:{locale}"
    cached = _cache_get(cache_key, ttl=3600)
    if isinstance(cached, list):
        return cached

    items = _builtin_location_items(query, limit, locale=locale)

    items.extend(await _search_nominatim_locations(query, limit, scope=scope, locale=locale))

    geocode_results: list[dict] = []
    should_merge_geocoding = (
        (not items)
        or scope == "global"
        or _contains_latin_letters(query)
        or any(
            not _looks_like_china_country(str(item.get("country", ""))) and not item.get("timezone")
            for item in items[:3]
        )
    )
    if should_merge_geocoding:
        geocode_count = max(limit * 2, 8)
        if scope in {"auto", "cn"}:
            try:
                data = await _fetch_geocoding(
                    query,
                    count=geocode_count,
                    country_code="CN",
                    language=locale,
                )
                results = data.get("results") if isinstance(data, dict) else None
                if isinstance(results, list):
                    geocode_results.extend(results)
            except (httpx.HTTPError, TypeError, ValueError, JSONDecodeError):
                logger.warning("[Context] Failed to search CN locations for query=%s", query, exc_info=True)

        if not geocode_results and scope in {"auto", "global"}:
            try:
                data = await _fetch_geocoding(query, count=geocode_count, language=locale)
                results = data.get("results") if isinstance(data, dict) else None
                if isinstance(results, list):
                    geocode_results.extend(results)
            except (httpx.HTTPError, TypeError, ValueError, JSONDecodeError):
                logger.warning("[Context] Failed to search global locations for query=%s", query, exc_info=True)

        for raw in geocode_results:
            parsed = _parse_geocoding_item(raw)
            if parsed and _location_matches_query(parsed, query):
                items.append(parsed)

    filtered_items = _refine_location_items(items, query)
    deduped = _dedupe_location_items(filtered_items, limit)
    _cache_set(cache_key, deduped)
    return deduped


async def _resolve_city_coords(city: str | None) -> tuple[float, float]:
    """Resolve city name to (lat, lon).

    Priority:
    1) CITY_COORDINATES exact match / fuzzy contains match
    2) Open-Meteo Geocoding API (cached)
    3) DEFAULT_LATITUDE/DEFAULT_LONGITUDE fallback
    """
    if not city:
        return DEFAULT_LATITUDE, DEFAULT_LONGITUDE

    coords = CITY_COORDINATES.get(city)
    if coords:
        return coords

    normalized = _normalize_place_name(city)
    for name, c in CITY_COORDINATES.items():
        if _normalize_place_name(name) == normalized:
            return c

    cache_key = f"geocode:{city}"
    cached = _cache_get(cache_key, ttl=86400)
    if cached is not None and isinstance(cached, (tuple, list)) and len(cached) == 2:
        try:
            return float(cached[0]), float(cached[1])
        except (TypeError, ValueError):
            pass

    try:
        results = await search_locations(city, limit=1)
        if results:
            lat_f = float(results[0]["latitude"])
            lon_f = float(results[0]["longitude"])
            _cache_set(cache_key, (lat_f, lon_f))
            return lat_f, lon_f
    except (httpx.HTTPError, TypeError, ValueError, JSONDecodeError, Exception):
        logger.warning("[Context] Failed to geocode city=%s, fallback to default", city, exc_info=True)

    return DEFAULT_LATITUDE, DEFAULT_LONGITUDE

