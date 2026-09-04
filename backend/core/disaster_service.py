"""
自然灾害预警引擎与多源警报服务 (Natural Disaster Alert Service)
负责获取中国气象局/和风天气官方气象灾害预警，进行等级严重度映射、缓存与最高优先级抢占。
"""
from __future__ import annotations

import io
import logging
import time
from typing import Any, Optional
from json import JSONDecodeError

import httpx
from PIL import Image

from .config import (
    DEFAULT_LATITUDE,
    DEFAULT_LONGITUDE,
    QWEATHER_API_HOST,
    QWEATHER_API_KEY,
)
from .weather_service import _qweather_get, _qweather_has_credentials
from .location_service import _resolve_city_coords

logger = logging.getLogger(__name__)

# 预警缓存: f"{lat},{lon}" -> (timestamp, list[dict])
_ALERT_CACHE: dict[str, tuple[float, list[dict[str, Any]]]] = {}
_ALERT_CACHE_TTL = 180.0  # 3分钟实时轮询缓存

# 模拟/人工测试预警寄存器: mac -> alert_dict
_SIMULATED_ALERTS: dict[str, dict[str, Any]] = {}

# 预警等级权重字典 (数值越小严重度越高)
LEVEL_SEVERITY: dict[str, int] = {
    "red": 1,
    "红色": 1,
    "i": 1,
    "i级": 1,
    "orange": 2,
    "橙色": 2,
    "ii": 2,
    "ii级": 2,
    "yellow": 3,
    "黄色": 3,
    "iii": 3,
    "iii级": 3,
    "blue": 4,
    "蓝色": 4,
    "iv": 4,
    "iv级": 4,
    "white": 5,
    "白色": 5,
}

# 国家气象防灾减灾标准四级预警体系规范
STANDARD_WARNING_LEVELS: dict[int, dict[str, str]] = {
    1: {
        "name": "红色预警",
        "short_name": "红色",
        "roman": "I级",
        "severity_desc": "特别严重",
        "urgency_label": "全社会最高警戒",
        "eink_color": "red",
    },
    2: {
        "name": "橙色预警",
        "short_name": "橙色",
        "roman": "II级",
        "severity_desc": "严重",
        "urgency_label": "紧急防御防范",
        "eink_color": "red",
    },
    3: {
        "name": "黄色预警",
        "short_name": "黄色",
        "roman": "III级",
        "severity_desc": "较重",
        "urgency_label": "密切防范准备",
        "eink_color": "black",
    },
    4: {
        "name": "蓝色预警",
        "short_name": "蓝色",
        "roman": "IV级",
        "severity_desc": "一般",
        "urgency_label": "注意防灾避险",
        "eink_color": "black",
    },
}


def normalize_warning_level(level_raw: str) -> tuple[int, dict[str, str]]:
    """规范化预警等级，返回标准 (等级代码 1~4, 等级元数据字典)。"""
    raw_str = (level_raw or "黄色").strip().lower()

    # 1. 优先按国家标准颜色字符判断
    if "红" in raw_str or "red" in raw_str:
        score = 1
    elif "橙" in raw_str or "orange" in raw_str:
        score = 2
    elif "黄" in raw_str or "yellow" in raw_str:
        score = 3
    elif "蓝" in raw_str or "blue" in raw_str:
        score = 4
    # 2. 罗马数字级别判断 (按长度降序，防止 'i' 误伤 'iv')
    elif "iv" in raw_str:
        score = 4
    elif "iii" in raw_str:
        score = 3
    elif "ii" in raw_str:
        score = 2
    elif "i" in raw_str:
        score = 1
    else:
        score = 3

    meta = STANDARD_WARNING_LEVELS.get(score, STANDARD_WARNING_LEVELS[3])
    return score, meta

# 灾害名称 -> 图标映射
HAZARD_NAME_TO_KEY: dict[str, str] = {
    "台风": "typhoon",
    "飓风": "typhoon",
    "暴雨": "rainstorm",
    "雷雨大风": "gale",
    "暴雪": "blizzard",
    "寒潮": "cold_wave",
    "大风": "gale",
    "沙尘暴": "sandstorm",
    "高温": "extreme_heat",
    "干旱": "extreme_heat",
    "雷电": "gale",
    "冰雹": "hail",
    "霜冻": "cold_wave",
    "大雾": "fog",
    "霾": "fog",
    "道路结冰": "blizzard",
    "森林火险": "wildfire",
    "地震": "earthquake",
    "海啸": "tsunami",
}


def _map_hazard_to_key(type_name: str, title: str = "") -> str:
    combined = f"{type_name} {title}"
    for k, v in HAZARD_NAME_TO_KEY.items():
        if k in combined:
            return v
    return "typhoon"


def _generate_default_advice(hazard_key: str) -> list[str]:
    """若官方预警未附带防御指南，自动生成标准避险建议。"""
    advices = {
        "typhoon": [
            "关好门窗，加固室外易被吹动的搭建物与花盆。",
            "切勿随意外出，远离广告牌、大树及临时工棚。",
            "停止露天集体活动和高空作业，警惕强降水。",
        ],
        "rainstorm": [
            "地势低洼居民区做好防涝排涝准备，切断低洼室外电源。",
            "行人和车辆避开涵洞、立交桥下等积水路段。",
            "山区居民注意防范山洪、滑坡和泥石流地质灾害。",
        ],
        "blizzard": [
            "减少不必要出行，外出注意防滑防冻。",
            "车辆安装防滑链，保持安全车距减速慢行。",
            "农牧区做好牲畜棚舍防风加固与牲畜保暖防冻。",
        ],
        "gale": [
            "关好门窗，加固围板、棚架等易被风吹落的搭建物。",
            "行人不要在老旧建筑物、大树、电线杆附近避风。",
            "水上作业和过往船舶应当及时回港避风。",
        ],
        "extreme_heat": [
            "午后高温时段尽量避免长时间户外活动。",
            "注意防暑降温，保障老人、儿童及户外工作者身体健康。",
            "注意用电安全，防范电路过载引发火灾。",
        ],
        "cold_wave": [
            "注意添衣保暖，防范呼吸道与心脑血管疾病。",
            "做好供暖、供水防冻保护与农业大棚保温。",
        ],
        "earthquake": [
            "保持冷静，震时就近躲避在坚固家具下或卫生间承重墙角。",
            "震后切断燃气与电源，迅速沿安全通道转移至开阔地带。",
            "远离高大建筑物、玻璃幕墙及高压电线。",
        ],
        "wildfire": [
            "严禁野外用火与丢弃烟头，加强森林防火巡查。",
            "发现火情立即撤离并拨打报警电话，切勿顺风逃生。",
        ],
    }
    return advices.get(hazard_key, [
        "密切关注气象部门发布的最新预警信号和应急指引。",
        "储备必要的生活应急物资，注意人身与财产安全。",
        "如遇险情立即向当地应急救援管理部门寻求帮助。",
    ])


async def fetch_active_alerts(lat: float, lon: float, city: str = "") -> list[dict[str, Any]]:
    """获取指定地理位置当前的全部生效气象自然灾害预警。"""
    cache_key = f"{round(lat, 2)},{round(lon, 2)}"
    now = time.time()
    cached = _ALERT_CACHE.get(cache_key)
    if cached and (now - cached[0] < _ALERT_CACHE_TTL):
        return cached[1]

    alerts: list[dict[str, Any]] = []

    # 1. 尝试和风天气官方预警 API
    if _qweather_has_credentials():
        try:
            location_str = f"{round(lon, 2)},{round(lat, 2)}"
            data = await _qweather_get("/v7/warning/now", {"location": location_str})
            if data and "warning" in data and isinstance(data["warning"], list):
                for item in data["warning"]:
                    lvl = item.get("level", "黄色")
                    t_name = item.get("typeName", "灾害")
                    title = item.get("title") or f"{t_name}{lvl}预警"
                    h_key = _map_hazard_to_key(t_name, title)
                    txt = item.get("text") or ""
                    adv = _generate_default_advice(h_key)

                    alerts.append({
                        "id": item.get("id") or str(time.time()),
                        "sender": item.get("sender") or "气象台",
                        "pub_time": item.get("pubTime", "")[:16].replace("T", " "),
                        "title": title,
                        "level": lvl,
                        "severity_score": LEVEL_SEVERITY.get(lvl.lower(), 3),
                        "type_name": t_name,
                        "hazard_key": h_key,
                        "text": txt,
                        "advice": adv,
                        "source": "qweather",
                    })
        except Exception as exc:
            logger.warning("[DisasterService] Failed to fetch QWeather warning: %s", exc)

    # 按严重程度排序 (1最严重排最前)
    alerts.sort(key=lambda x: x.get("severity_score", 4))
    _ALERT_CACHE[cache_key] = (now, alerts)
    return alerts


def simulate_disaster_alert(mac: str, alert_override: dict[str, Any] | None = None) -> dict[str, Any]:
    """为指定设备写入模拟灾害预警，供测试与应急演练。"""
    default_sim = {
        "id": f"sim-{int(time.time())}",
        "sender": "国家应急气象预警中心",
        "pub_time": time.strftime("%Y-%m-%d %H:%M"),
        "title": "台风红色预警 [I级/特别严重]",
        "level": "红色",
        "severity_score": 1,
        "type_name": "超强台风",
        "hazard_key": "typhoon",
        "text": "受超强台风中心外围螺旋雨带影响，未来12小时本市将出现平均风力12级以上阵风，伴随特大暴雨与风暴潮，请全面启动防风防汛应急响应。",
        "advice": [
            "全民进入紧急防风防汛状态，实行停课、停工、停市、停运。",
            "沿海低洼地带、临海建筑内人员务必全部撤离至避护中心。",
            "关闭燃气总阀并切断非必要电源，切勿在树木及临时建筑下逗留。",
        ],
        "source": "simulation",
    }
    if alert_override:
        default_sim.update(alert_override)
    _SIMULATED_ALERTS[mac.upper()] = default_sim
    return default_sim


def clear_simulated_alert(mac: str) -> None:
    """清除设备的模拟预警。"""
    _SIMULATED_ALERTS.pop(mac.upper(), None)


async def check_device_disaster_alert(mac: str, cfg: dict | None) -> dict[str, Any] | None:
    """检查设备是否启用了灾害预警监听，并判断是否有达到严重度门槛的有效警报。
    增加严格的地区归属匹配与防误判机制，杜绝远距离无关地区的灾害预警误触发设备全屏避险。
    """
    norm_mac = (mac or "").upper()

    # 1. 优先检查模拟/演练中的预警
    if norm_mac in _SIMULATED_ALERTS:
        return _SIMULATED_ALERTS[norm_mac]

    if not cfg:
        return None

    alert_cfg = cfg.get("disaster_alert") or {}
    if not alert_cfg.get("enabled", False):
        return None

    # 最低告警级别门槛 (默认 yellow: 黄、橙、红均报警)
    min_level_name = alert_cfg.get("min_level", "yellow").lower()
    threshold_score = LEVEL_SEVERITY.get(min_level_name, 3)

    # 确定监控的城市与经纬度
    city = (alert_cfg.get("city") or cfg.get("city") or "").strip()
    lat = alert_cfg.get("latitude") or cfg.get("latitude")
    lon = alert_cfg.get("longitude") or cfg.get("longitude")
    if lat is None or lon is None:
        lat, lon = await _resolve_city_coords(city)

    active_alerts = await fetch_active_alerts(float(lat), float(lon), city)
    for al in active_alerts:
        # 严重度门槛过滤
        if al.get("severity_score", 4) > threshold_score:
            continue

        # 地区精准匹配与防误判检验
        # 如果预警文本或标题含有地域信息，确保与配置的城市地区一致或重叠
        if city:
            c_norm = city.replace("市", "").replace("区", "").replace("县", "")
            al_sender = al.get("sender", "")
            al_title = al.get("title", "")
            al_text = al.get("text", "")
            combined_geo = f"{al_sender} {al_title} {al_text}"

            # 如果预警来源于特定地方台发布（包含“气象台”），检查是否与本市一致
            if "气象台" in al_sender:
                # 地方台发布若明确包含其他城市且完全不包含本市，则判定为非本区预警，予以拦截
                if c_norm and (c_norm not in combined_geo):
                    # 仅当 sender/title 明确属于省外或别市台发布时过滤
                    logger.debug(
                        "[DisasterService] Mismatched city alert filtered: device_city=%s, sender=%s",
                        city,
                        al_sender,
                    )
                    continue

        return al

    return None


def build_disaster_alert_mode_def(alert: dict[str, Any]) -> dict[str, Any]:
    """构建用于墨水屏渲染的最高优先级全屏紧急避险 JSON 布局定义。"""
    lvl = alert.get("level", "红色")
    hazard = alert.get("type_name", "气象自然灾害")
    hazard_key = alert.get("hazard_key", "typhoon")
    sender = alert.get("sender", "国家应急防灾指挥中心")
    pub_time = alert.get("pub_time", "")
    text_content = alert.get("text", "")
    advices = alert.get("advice") or _generate_default_advice(hazard_key)

    is_red = "红" in lvl or "RED" in lvl.upper()
    theme_color = "red" if is_red else "black"

    mode_def = {
        "mode_id": "DISASTER_ALERT",
        "display_name": "自然灾害紧急预警",
        "cacheable": False,
        "content": {
            "type": "static",
            "text": text_content,
            "advice": advices,
        },
        "layout": {
            "body_align": "top",
            "body": [
                {
                    "type": "header_banner",
                    "style": "inverted",
                    "bg_color": theme_color,
                    "title": "自然灾害紧急通报",
                    "badge": f"{lvl}预警",
                    "right_text": "HIGHEST PRIORITY",
                    "height": 32,
                    "margin_bottom": 6,
                },
                {
                    "type": "disaster_banner",
                    "level": lvl,
                    "hazard": hazard,
                    "sender": sender,
                    "time": pub_time,
                    "height": 44,
                    "margin_bottom": 5,
                },
                {
                    "type": "disaster_level_meter",
                    "level": lvl,
                    "height": 20,
                    "margin_bottom": 6,
                },
                {
                    "type": "disaster_icon",
                    "hazard": hazard_key,
                    "size": 42,
                    "align": "center",
                    "color": "black",
                    "accent_color": theme_color,
                    "margin_bottom": 6,
                },
                {
                    "type": "text",
                    "field": "text",
                    "font": "noto_serif_regular",
                    "font_size": 12,
                    "line_height": 17,
                    "align": "left",
                    "margin_x": 14,
                    "max_lines": 3,
                    "margin_bottom": 6,
                },
                {
                    "type": "disaster_advice_box",
                    "title": "防灾避险关键指引",
                    "items": advices,
                    "margin_x": 12,
                    "margin_bottom": 4,
                },
            ],
            "footer": {
                "label": "防灾应急特别广播",
                "attribution_template": "{pub_time}" if pub_time else "防灾减灾 人人有责",
            }
        }
    }
    return mode_def
