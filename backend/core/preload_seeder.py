"""
预存数据种子加载器
负责在服务启动时，为 THISDAY（未来 7~14 天）以及 DAILY / WORD_OF_THE_DAY / MY_QUOTE 自动预置高质量条目。
"""
from __future__ import annotations

import logging
from datetime import date, timedelta

from .preload_store import add_preload_item, get_preload_count

logger = logging.getLogger(__name__)

# 预存高质量历史上的今天事件（按日历月日组织）
_THISDAY_SEEDS_BY_MD: dict[tuple[int, int], list[dict[str, str]]] = {
    # 9月4日
    (9, 4): [
        {
            "year": "1888",
            "event_title": "柯达相机诞生",
            "event_desc": "乔治·伊士曼获得卷轴胶卷相机专利，让摄影艺术从专业走向寻常百姓家。",
            "years_ago": "138年前",
            "significance": "开启大众影像记录时代",
        },
        {
            "year": "1998",
            "event_title": "谷歌公司正式成立",
            "event_desc": "拉里·佩奇和谢尔盖·布林在加州车库创办Google，重构了全球信息检索方式。",
            "years_ago": "28年前",
            "significance": "改变人类获取信息的方式",
        },
        {
            "year": "1972",
            "event_title": "马克·施皮茨七金创举",
            "event_desc": "在慕尼黑奥运会上，美国游泳名将施皮茨赢得个人第7枚金牌并全部打破世界纪录。",
            "years_ago": "54年前",
            "significance": "奥运史上的传奇神话",
        },
    ],
    # 9月5日
    (9, 5): [
        {
            "year": "1977",
            "event_title": "旅行者1号升空",
            "event_desc": "携带镀金唱片的旅行者1号探测器发射，飞向太阳系外无垠的深空。",
            "years_ago": "49年前",
            "significance": "人类迈向星际空间的使者",
        },
        {
            "year": "1905",
            "event_title": "《朴次茅斯和约》签订",
            "event_desc": "日俄战争正式宣告结束，对20世纪初东亚地缘格局产生深远影响。",
            "years_ago": "121年前",
            "significance": "远东现代史的关键转折",
        },
    ],
    # 9月6日
    (9, 6): [
        {
            "year": "1522",
            "event_title": "人类首次环球航行凯旋",
            "event_desc": "麦哲伦船队的维多利亚号重返西班牙港口，直观证明了地球是球形的真理。",
            "years_ago": "504年前",
            "significance": "地理大发现的巅峰时刻",
        },
        {
            "year": "1991",
            "event_title": "圣彼得堡恢复原名",
            "event_desc": "俄罗斯城市列宁格勒经市民投票表决，正式恢复具有历史意义的圣彼得堡旧名。",
            "years_ago": "35年前",
            "significance": "见证一个历史时代的落幕与重生",
        },
    ],
    # 9月7日
    (9, 7): [
        {
            "year": "1901",
            "event_title": "《辛丑条约》签订",
            "event_desc": "近代中国与列强签订赔款数额最为庞大的不平等条约，警示后人当自强不息。",
            "years_ago": "125年前",
            "significance": "近代历史的沉痛教训",
        },
        {
            "year": "1822",
            "event_title": "巴西宣布独立",
            "event_desc": "佩德罗一世在伊皮兰加河畔高呼'不独立毋宁死'，宣告巴西脱离葡萄牙独立。",
            "years_ago": "204年前",
            "significance": "拉美民族独立运动的壮举",
        },
    ],
    # 9月8日
    (9, 8): [
        {
            "year": "1966",
            "event_title": "《星际迷航》首播",
            "event_desc": "科幻巨作《星际迷航》电视系列首播，名言'生生不息，繁荣昌盛'传颂至今。",
            "years_ago": "60年前",
            "significance": "现代流行科幻文化的里程碑",
        },
        {
            "year": "1945",
            "event_title": "美军进驻朝鲜半岛南部",
            "event_desc": "美军在仁川登陆，朝鲜半岛以三八线为界的冷战对峙格局初步形成。",
            "years_ago": "81年前",
            "significance": "战后冷战格局的重要开端",
        },
    ],
    # 9月9日
    (9, 9): [
        {
            "year": "1947",
            "event_title": "计算机史上第一只Bug诞生",
            "event_desc": "葛丽丝·霍普团队在Mark II计算机继电器中捉出一只飞蛾，Bug一词正式载入科技史册。",
            "years_ago": "79年前",
            "significance": "软件工程 Debug 概念的起源",
        },
        {
            "year": "1850",
            "event_title": "加利福尼亚加入美国",
            "event_desc": "伴随着淘金热的高潮，加利福尼亚作为第31个州正式加入美利坚合众国。",
            "years_ago": "176年前",
            "significance": "美国西海岸发展的转折点",
        },
    ],
    # 9月10日
    (9, 10): [
        {
            "year": "1898",
            "event_title": "茜茜公主遇刺",
            "event_desc": "奥匈帝国皇后伊丽莎白在日内瓦湖畔遇刺身亡，一位传奇皇后的绝美画卷谢幕。",
            "years_ago": "128年前",
            "significance": "欧洲王室凄美绝伦的时代记忆",
        },
        {
            "year": "1985",
            "event_title": "中国第一个教师节",
            "event_desc": "中国迎来新中国成立后的首个教师节，尊师重道、教书育人成为时代新风尚。",
            "years_ago": "41年前",
            "significance": "全社会尊重知识与教育的起点",
        },
    ],
}

# 预存通用名言库 (DAILY / MY_QUOTE / STOIC)
_QUOTE_SEEDS = [
    {"quote": "把今天过好，就是对未来最好的投资。", "author": "罗曼·罗兰"},
    {"quote": "阻碍行动的障碍，本身就是行动的路。", "author": "马可·奥勒留"},
    {"quote": "宁静不是避开风暴，而是在风暴深处保持内心的平稳。", "author": "塞涅卡"},
    {"quote": "知止而后有定，定而后能静，静而后能安。", "author": "《大学》"},
    {"quote": "博观而约取，厚积而薄发。", "author": "苏轼"},
    {"quote": "我们所经历的每一个清晨，都是生活赐予的崭新白纸。", "author": "纪伯伦"},
    {"quote": "行到水穷处，坐看云起时。", "author": "王维"},
    {"quote": "凡是过往，皆为序章；凡是未来，皆有可期。", "author": "莎士比亚"},
]

# 预存通用词汇库 (WORD_OF_THE_DAY)
_WORD_SEEDS = [
    {
        "word": "Serendipity",
        "phonetic": "/ˌser.ənˈdɪp.ə.ti/",
        "definition": "意外发现美好事物的能力",
        "example": "Traveling often brings serendipity and wonder.",
    },
    {
        "word": "Petrichor",
        "phonetic": "/ˈpet.rɪ.kɔːr/",
        "definition": "雨后泥土散发出的清香",
        "example": "The crisp petrichor filled the forest after the rain.",
    },
    {
        "word": "Ephemeral",
        "phonetic": "/ɪˈfem.ər.əl/",
        "definition": "短暂的，转瞬即逝的美好",
        "example": "Cherry blossoms are stunning yet ephemeral.",
    },
    {
        "word": "Resilience",
        "phonetic": "/rɪˈzɪl.jəns/",
        "definition": "韧性，快速自愈的能力",
        "example": "True strength lies in quiet resilience.",
    },
    {
        "word": "Luminescence",
        "phonetic": "/ˌluː.mɪˈnes.əns/",
        "definition": "冷光，暗夜里微弱的光亮",
        "example": "The soft luminescence of fireflies lit the path.",
    },
]


async def seed_preload_pool(days_ahead: int = 14) -> None:
    """自动补充未来 N 天的预存历史事件及通用滚动池。"""
    today = date.today()

    # 1. 补充未来 days_ahead 天的历史事件
    for i in range(days_ahead):
        d = today + timedelta(days=i)
        d_str = d.isoformat()
        md = (d.month, d.day)

        events = _THISDAY_SEEDS_BY_MD.get(md, [])
        if not events:
            # 兜底生成通用历史事件，保证每一天都有饱满内容
            events = [
                {
                    "year": "1969",
                    "event_title": "人类太空探索里程碑",
                    "event_desc": "人类迈出了探索地外星体的一大步，见证勇气与好奇心。",
                    "years_ago": f"{d.year - 1969}年前",
                    "significance": "科学与文明的伟大见证",
                },
                {
                    "year": "1928",
                    "event_title": "现代抗生素的发现",
                    "event_desc": "科学家偶然发现青霉菌抑制细菌生长的现象，挽救了数以亿计的生命。",
                    "years_ago": f"{d.year - 1928}年前",
                    "significance": "现代医学拯救生命的转折点",
                },
            ]

        for ev in events:
            await add_preload_item("THISDAY", ev, target_date=d_str)

    # 2. 补充 DAILY / MY_QUOTE
    for q in _QUOTE_SEEDS:
        await add_preload_item("DAILY", q)
        await add_preload_item("MY_QUOTE", q)
        await add_preload_item("STOIC", q)

    # 3. 补充 WORD_OF_THE_DAY
    for w in _WORD_SEEDS:
        await add_preload_item("WORD_OF_THE_DAY", w)

    logger.info("[Preload] Seeded preload pool for upcoming %d days.", days_ahead)
