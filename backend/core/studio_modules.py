"""
MindReset Studio 规范模块化元架构 (Module & Component Specification)
参考 dot.mindreset.tech/docs/service/studio 规范：
将 InkSight 的组件与模式按照【生活日常】、【效率工作】、【资讯热点】、【灵感创作】四个核心 Studio 分类组织，
并提供组件能力定义、输入参数 Schema、是否具备定时刷新与离线池自生长能力。
"""
from typing import Any

STUDIO_CATEGORIES = [
    {
        "id": "life",
        "name_zh": "生活日常",
        "name_en": "Life & Wellness",
        "icon": "Heart",
        "description": "天气时钟、倒数纪念日、每日金句、习惯打卡等陪伴生活的好物",
    },
    {
        "id": "productivity",
        "name_zh": "效率工作",
        "name_en": "Productivity & Focus",
        "icon": "Briefcase",
        "description": "待办清单、课程表、专注时钟、日程提醒等桌面效能伙伴",
    },
    {
        "id": "news",
        "name_zh": "资讯热点",
        "name_en": "News & Feeds",
        "icon": "Newspaper",
        "description": "网易云热歌、豆瓣电影、全网热搜、灾害预警等实时桌面资讯站",
    },
    {
        "id": "studio",
        "name_zh": "灵感创作",
        "name_en": "Creative Studio",
        "icon": "Sparkles",
        "description": "大模型哲学慢信、古诗新解、谜题、单词记忆与趣味互动",
    },
]

MODE_TO_STUDIO_CATEGORY: dict[str, str] = {
    # 资讯热点
    "HOTLIST": "news",
    "DISASTER_ALERT": "news",
    "WEB_NOTICE": "news",
    "RSS": "news",
    "STOCK": "news",
    "CRYPTO": "news",
    "GOLD": "news",
    "MARKET": "news",
    # 效率工作
    "TODO": "productivity",
    "TIMETABLE": "productivity",
    "CALENDAR": "productivity",
    "COUNTDOWN": "productivity",
    "HABIT": "productivity",
    "FOCUS": "productivity",
    "GITHUB": "productivity",
    # 生活日常
    "CLOCK": "life",
    "WEATHER": "life",
    "DAILY": "life",
    "STOIC": "life",
    "MY_QUOTE": "life",
    "WECHAT_READ": "life",
    "HEALTH": "life",
    "AIR": "life",
    # 灵感创作
    "WORD_OF_THE_DAY": "studio",
    "LETTER": "studio",
    "RIDDLE": "studio",
    "ROAST": "studio",
    "ZEN": "studio",
    "STORY": "studio",
    "POETRY": "studio",
    "QUESTION": "studio",
    "BIAS": "studio",
    "CHALLENGE": "studio",
}


def get_studio_category_for_mode(mode_id: str) -> str:
    """根据模式 ID 返回符合 MindReset Studio 规范的分类。"""
    return MODE_TO_STUDIO_CATEGORY.get(mode_id.upper(), "life")


def enrich_mode_with_studio_meta(mode_def: dict[str, Any]) -> dict[str, Any]:
    """为模式定义附加 Studio 规范分类与标签。"""
    m_id = mode_def.get("mode_id", "").upper()
    cat = get_studio_category_for_mode(m_id)
    enriched = dict(mode_def)
    enriched["studio_category"] = cat
    enriched["studio_spec_version"] = "1.0.0"
    return enriched
