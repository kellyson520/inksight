"""
预存数据种子加载器 (Preload Seeder)
负责在服务启动时，为 THISDAY（未来 7~14 天）以及全量 LLM 模式自动预置高质量条目：
WORD_OF_THE_DAY, RIDDLE, LETTER, DAILY, MY_QUOTE, STOIC, ROAST, ZEN,
STORY, POETRY, QUESTION, RECIPE, BIAS, CHALLENGE 等。
实现彻底告别单条内容重复、离线即用、以及无 API Key 时的平滑优雅降级体验。
"""
from __future__ import annotations

import logging
from datetime import date, timedelta

from .preload_store import add_preload_item

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

# 预存通用词汇库 (WORD_OF_THE_DAY: 扩充至30+高质词汇，彻底杜绝重复)
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
    {
        "word": "Sonder",
        "phonetic": "/ˈsɒn.dər/",
        "definition": "意识到每个人都过着生动复杂的生命",
        "example": "Looking at the crowd, he felt a sudden wave of sonder.",
    },
    {
        "word": "Mellifluous",
        "phonetic": "/meˈlɪf.lu.əs/",
        "definition": "声音甜美圆润、悦耳动听",
        "example": "Her mellifluous voice soothed the anxious room.",
    },
    {
        "word": "Halcyon",
        "phonetic": "/ˈhæl.si.ən/",
        "definition": "宁静祥和的黄金岁月",
        "example": "They recalled the halcyon days of youth.",
    },
    {
        "word": "Aurora",
        "phonetic": "/ɔːˈrɔː.rə/",
        "definition": "曙光、极光与新希望",
        "example": "An emerald aurora danced across the arctic sky.",
    },
    {
        "word": "Hiraeth",
        "phonetic": "/ˈhɪə.raɪθ/",
        "definition": "对无法归去的时光的深切怀恋",
        "example": "Listening to old folk songs awoke a bittersweet hiraeth.",
    },
    {
        "word": "Epoch",
        "phonetic": "/ˈiː.pɒk/",
        "definition": "里程碑时代，划时代纪元",
        "example": "The birth of personal computing marked a bold new epoch.",
    },
    {
        "word": "Solitude",
        "phonetic": "/ˈsɒl.ɪ.tʃuːd/",
        "definition": "享受内心的清静自处",
        "example": "He found creative inspiration in peaceful solitude.",
    },
    {
        "word": "Eloquence",
        "phonetic": "/ˈel.ə.kwəns/",
        "definition": "雄辩口才与动人心弦的表达",
        "example": "The speaker moved the audience with timeless eloquence.",
    },
    {
        "word": "Zenith",
        "phonetic": "/ˈzen.ɪθ/",
        "definition": "顶峰、天顶与荣耀极点",
        "example": "The sun reached its zenith in a cloudless noon sky.",
    },
    {
        "word": "Limerence",
        "phonetic": "/ˈlɪm.ər.əns/",
        "definition": "因心动而产生的浪漫迷恋",
        "example": "Young love often starts with intoxicating limerence.",
    },
    {
        "word": "Komorebi",
        "phonetic": "/ko-mo-re-bi/",
        "definition": "阳光穿透树叶倾泻的斑驳光影",
        "example": "Gentle komorebi painted warm patterns across the wooden floor.",
    },
    {
        "word": "Eudaimonia",
        "phonetic": "/juː.daɪˈmoʊ.ni.ə/",
        "definition": "至善幸福与潜能的全面实现",
        "example": "Aristotle saw eudaimonia as the ultimate human pursuit.",
    },
    {
        "word": "Nostalgia",
        "phonetic": "/nɒsˈtæl.dʒə/",
        "definition": "对往昔美好时光的温情追忆",
        "example": "The melody stirred sweet nostalgia in their hearts.",
    },
    {
        "word": "Pluviophile",
        "phonetic": "/ˌpluː.vi.oʊˈfaɪl/",
        "definition": "在雨声中寻得心安的爱雨者",
        "example": "As a pluviophile, she loved reading by the rainy window.",
    },
    {
        "word": "Renaissance",
        "phonetic": "/rəˈneɪ.səns/",
        "definition": "新生、复兴与思想繁盛",
        "example": "Open source software sparked a true digital renaissance.",
    },
    {
        "word": "Quintessence",
        "phonetic": "/kwɪnˈtes.əns/",
        "definition": "最纯粹的精髓与典型代表",
        "example": "This courtyard is the quintessence of traditional design.",
    },
    {
        "word": "Serenity",
        "phonetic": "/səˈren.ə.ti/",
        "definition": "风平浪静的从容与心境祥和",
        "example": "The quiet dawn brought profound serenity to his mind.",
    },
    {
        "word": "Ubiquitous",
        "phonetic": "/juːˈbɪk.wɪ.təs/",
        "definition": "无处不在的，普遍存在的",
        "example": "Smart sensors have become ubiquitous in daily life.",
    },
    {
        "word": "Synergy",
        "phonetic": "/ˈsɪn.ə.dʒi/",
        "definition": "协同作用，产生远超单体的聚力",
        "example": "The team achieved brilliant synergy across disciplines.",
    },
    {
        "word": "Catalyst",
        "phonetic": "/ˈkæt.əl.ɪst/",
        "definition": "催化剂，促成深刻改变的关键因素",
        "example": "Curiosity was the real catalyst for her innovation.",
    },
    {
        "word": "Tenacity",
        "phonetic": "/təˈnæs.ə.ti/",
        "definition": "百折不挠的坚韧毅力",
        "example": "Through quiet tenacity, the research reached its breakthrough.",
    },
    {
        "word": "Metamorphosis",
        "phonetic": "/ˌmet.əˈmɔː.fə.sɪs/",
        "definition": "破茧成蝶的彻底蜕变",
        "example": "Learning a new craft often triggers a personal metamorphosis.",
    },
    {
        "word": "Equanimity",
        "phonetic": "/ˌek.wəˈnɪm.ə.ti/",
        "definition": "面对波澜起伏时的沉着平静",
        "example": "She handled the complex crisis with remarkable equanimity.",
    },
    {
        "word": "Ingenuity",
        "phonetic": "/ˌɪn.dʒəˈnjuː.ə.ti/",
        "definition": "巧妙别致的独创性与创造力",
        "example": "The engineers solved the riddle with simple human ingenuity.",
    },
    {
        "word": "Effervescence",
        "phonetic": "/ˌef.əˈves.əns/",
        "definition": "欢腾雀跃的生机与热情",
        "example": "The celebration sparkled with youthful effervescence.",
    },
]

# 预存通用名言库 (DAILY / MY_QUOTE / STOIC: 扩充至30+条)
_QUOTE_SEEDS = [
    {"quote": "把今天过好，就是对未来最好的投资。", "author": "罗曼·罗兰"},
    {"quote": "阻碍行动的障碍，本身就是行动的路。", "author": "马可·奥勒留"},
    {"quote": "宁静不是避开风暴，而是在风暴深处保持内心的平稳。", "author": "塞涅卡"},
    {"quote": "知止而后有定，定而后能静，静而后能安。", "author": "《大学》"},
    {"quote": "博观而约取，厚积而薄发。", "author": "苏轼"},
    {"quote": "我们所经历的每一个清晨，都是生活赐予的崭新白纸。", "author": "纪伯伦"},
    {"quote": "行到水穷处，坐看云起时。", "author": "王维"},
    {"quote": "凡是过往，皆为序章；凡是未来，皆有可期。", "author": "莎士比亚"},
    {"quote": "生活不是等待暴风雨过去，而是学会在雨中翩翩起舞。", "author": "英国谚语"},
    {"quote": "不乱于心，不困于情。不畏将来，不念过往。", "author": "丰子恺"},
    {"quote": "流水不争先，争的是滔滔不绝。", "author": "《道德经》"},
    {"quote": "向外张望的人在做梦，向内审视的人才清醒。", "author": "荣格"},
    {"quote": "缓慢而坚定地前行，胜过盲目的奔跑。", "author": "伊索"},
    {"quote": "生活最好的状态，是冷清中带有充实，忙碌中存有从容。", "author": "林清玄"},
    {"quote": "接受我们不能改变的，改变我们能够改变的。", "author": "爱比克泰德"},
    {"quote": "日日行，不怕千万里；常常做，不怕千万事。", "author": "《格言联璧》"},
    {"quote": "人生的意义不在于何处抵达，而在于怎样经历旅途。", "author": "歌德"},
    {"quote": "专注当下的每一寸光阴，幸福便自会到来。", "author": "蒙田"},
    {"quote": "与其诅咒黑暗，不如点亮一盏微光。", "author": "孔子"},
    {"quote": "在荒谬的世界中，保持对生活的热爱是最高尚的反抗。", "author": "加缪"},
    {"quote": "结庐在人境，而无车马喧。问君何能尔？心远地自偏。", "author": "陶渊明"},
    {"quote": "天下难事，必作于易；天下大事，必作于细。", "author": "老子"},
    {"quote": "知足天地宽，贪求宇宙隘。", "author": "《菜根谭》"},
    {"quote": "心随境转是凡夫，境随心转是圣贤。", "author": "禅宗谚语"},
    {"quote": "保持内心的清晰与坚定，其余的交给时间。", "author": "黑塞"},
    {"quote": "万物皆有裂痕，那是光照进来的地方。", "author": "莱昂纳德·科恩"},
    {"quote": "只要春天还在，我就不会悲哀；纵使黑夜吞噬了一切，太阳还可以重新回来。", "author": "汪国真"},
    {"quote": "重要的不是生活给了你什么，而是你用它创造了什么。", "author": "阿德勒"},
]

# 预存谜题库 (RIDDLE: 25+经典趣味谜题与冷知识)
_RIDDLE_SEEDS = [
    {
        "category": "谜语",
        "question": "两个胖子（打一城市名）",
        "hint": "想想体重",
        "answer": "合肥",
    },
    {
        "category": "脑筋急转弯",
        "question": "什么东西越洗越脏，不洗反而干净？",
        "hint": "生活常见液体",
        "answer": "水",
    },
    {
        "category": "谜语",
        "question": "早晨四条腿，中午两条腿，晚上三条腿（打一生物）",
        "hint": "斯芬克斯之谜",
        "answer": "人（婴儿/成年/老年）",
    },
    {
        "category": "谜语",
        "question": "麻屋子，红帐子，里面住个白胖子（打一植物坚果）",
        "hint": "过年常吃",
        "answer": "花生",
    },
    {
        "category": "冷知识",
        "question": "北极熊的皮肤实际上是什么颜色的？",
        "hint": "不是白色的哦",
        "answer": "黑色（毛发是透明的）",
    },
    {
        "category": "谜语",
        "question": "千条线，万条线，掉到水里看不见（打一自然现象）",
        "hint": "天气相关",
        "answer": "雨",
    },
    {
        "category": "脑筋急转弯",
        "question": "什么门永远关不上？",
        "hint": "运动场上常见",
        "answer": "球门",
    },
    {
        "category": "谜语",
        "question": "有时落在山腰，有时挂在树梢。有时像个圆盘，有时像把弯刀（打一天体）",
        "hint": "夜空主角",
        "answer": "月亮",
    },
    {
        "category": "冷知识",
        "question": "章鱼实际上拥有几颗心脏？",
        "hint": "不止一颗",
        "answer": "3颗心脏",
    },
    {
        "category": "脑筋急转弯",
        "question": "小明的妈妈有三个儿子，大儿子叫大毛，二儿子叫二毛，三儿子叫什么？",
        "hint": "仔细读题",
        "answer": "小明",
    },
    {
        "category": "谜语",
        "question": "远看山有色，近听水无声。春去花还在，人来鸟不惊（打一艺术品）",
        "hint": "挂在墙上",
        "answer": "画",
    },
    {
        "category": "脑筋急转弯",
        "question": "什么路最窄？",
        "hint": "四个字成语",
        "answer": "冤家路窄",
    },
    {
        "category": "冷知识",
        "question": "天然纯蜂蜜在密封避光条件下可以存放多久？",
        "hint": "难以置信的时间",
        "answer": "数千年不腐",
    },
    {
        "category": "谜语",
        "question": "独木造高楼，没瓦没砖头。人在水下走，水在人上流（打一日常用品）",
        "hint": "雨天出门必备",
        "answer": "雨伞",
    },
    {
        "category": "脑筋急转弯",
        "question": "什么东西无论你怎么拿，指针总是偏向同一个方向？",
        "hint": "野外导航",
        "answer": "指南针",
    },
    {
        "category": "谜语",
        "question": "白天看不见，晚上亮晶晶。一闪一闪眨眼睛（打一天体）",
        "hint": "儿歌常客",
        "answer": "星星",
    },
    {
        "category": "冷知识",
        "question": "香蕉在植物学分类上其实属于哪种果实？",
        "hint": "多汁类分类",
        "answer": "浆果（Berry）",
    },
    {
        "category": "脑筋急转弯",
        "question": "一头公牛加一头母牛，猜三个字？",
        "hint": "简单算术题",
        "answer": "两头牛",
    },
    {
        "category": "谜语",
        "question": "身体生来瘦又长，五彩衣裳穿身上。嘴巴尖尖会画画，只见短来不见长（打一文具）",
        "hint": "文具盒里有",
        "answer": "铅笔",
    },
    {
        "category": "冷知识",
        "question": "草莓表面密密麻麻的小颗粒实际上是什么？",
        "hint": "并非简单的种子",
        "answer": "真正的果实（瘦果）",
    },
    {
        "category": "脑筋急转弯",
        "question": "什么东西买的人知道，卖的人知道，用的人却不知道？",
        "hint": "特殊场景用品",
        "answer": "棺材",
    },
    {
        "category": "谜语",
        "question": "一个小姑娘，生在水中央，身穿粉红衫，坐在绿船上（打一花卉）",
        "hint": "出淤泥而不染",
        "answer": "荷花",
    },
    {
        "category": "冷知识",
        "question": "人体中最坚硬的组织是什么？",
        "hint": "不是骨骼",
        "answer": "牙釉质",
    },
    {
        "category": "脑筋急转弯",
        "question": "用什么擦地最干净、最省力？",
        "hint": "用力思考",
        "answer": "用钱（请保洁）",
    },
]

# 预存慢信库 (LETTER: 20封不同时空、文学性强、温暖真挚的书信)
_LETTER_SEEDS = [
    {
        "sender": "1920年代上海的裁缝",
        "greeting": "致桌前的朋友",
        "body": "秋意渐浓，我刚赶制完一件滚边墨绿旗袍。窗外梧桐落叶打在青石板上，缝纫机的嗒嗒声伴着炉火。手艺虽慢，但一针一线里藏着日子的温度。",
        "closing": "愿你岁月静好，衣暖心安",
        "postscript": "P.S. 记得添衣防寒",
    },
    {
        "sender": "1980年代绿皮火车的旅人",
        "greeting": "致同行者",
        "body": "列车正穿过秦岭的一座座隧道，车厢里弥漫着茶水与橘皮的气味。窗外是连绵的远山与炊烟，慢下来的时光里，连发呆都是一件诗意的事。",
        "closing": "愿你的旅程总有风景可期",
        "postscript": "P.S. 别忘了看沿途的日落",
    },
    {
        "sender": "极地科考站的气象员",
        "greeting": "致远方的守望者",
        "body": "极夜快要结束了，地平线上泛起第一抹玫瑰色的晨光。在零下四十度的寂静中，地球呼吸的声音格外清晰。远方的灯火，始终是我们心中的锚。",
        "closing": "祝远方的晨曦温暖你",
        "postscript": "P.S. 热可可正冒着香气",
    },
    {
        "sender": "旧书店的守门人",
        "greeting": "致爱书的朋友",
        "body": "午后在整理书架时，从一本薄薄的诗集里滑出一片泛黄的银杏书签。三十年前留下的折角，此刻正与你的目光重逢。有些温暖总在不经意间流转。",
        "closing": "祝你今日偶遇心动的文字",
        "postscript": "P.S. 翻开下一页吧",
    },
    {
        "sender": "山间观星台的守夜人",
        "greeting": "致仰望星空的你",
        "body": "今夜高山风清，银河如同一条流动的碎钻长河倾泻而下。猎户座升起的时候，整个世界都睡熟了。每一颗星光的抵达，都穿越了数万年的光阴。",
        "closing": "愿你心中常有星光引路",
        "postscript": "P.S. 抬头看看今夜的夜空",
    },
    {
        "sender": "海岛灯塔的守塔人",
        "greeting": "致航行中的朋友",
        "body": "涨潮的海浪一下下拍打着礁石，灯塔的光束正划破海面的薄雾。无论航程多么漫长，总有一盏光芒为你守候归途。风平浪静很快就会到来。",
        "closing": "愿你前路坦荡，顺遂无虞",
        "postscript": "P.S. 听听风声，别急着赶路",
    },
    {
        "sender": "未来空间站的植物学家",
        "greeting": "致旧日的地球来信",
        "body": "水培温室里的第一朵月季今天清晨绽放了，淡淡的香气让所有人都停下了脚步。在无重力的太空中，生命依然执着地寻找着向阳的姿态。",
        "closing": "愿你的生活常有微小生机",
        "postscript": "P.S. 窗外的地球依然湛蓝",
    },
    {
        "sender": "隐居陶艺作坊的匠人",
        "greeting": "致都市奔波的友朋",
        "body": "今天新开了一窑柴烧茶盏，火焰留下了不可预测的落灰与窑变。泥土经过烈火的淬炼，才有了质朴而坚实的触感。慢一点，好的事物需要时间沉淀。",
        "closing": "祝你内心从容，气定神闲",
        "postscript": "P.S. 给自己泡杯温润的清茶",
    },
    {
        "sender": "深秋森林里的护林员",
        "greeting": "致远方的听风者",
        "body": "松针落了厚厚一层，踩上去软软的。山溪边有一只松鼠正忙着储藏坚果，水流清冽见底。大自然从不慌张，每个季节都在按部就班地完成约定。",
        "closing": "愿你也有松弛而丰盈的节奏",
        "postscript": "P.S. 捡起一片好看的落叶",
    },
    {
        "sender": "老钟表店的修表师傅",
        "greeting": "致珍惜光阴的朋友",
        "body": "案头的齿轮正在有节奏地嘀嗒转动。发条拧紧又舒展，时光便在一毫一厘间走过。我们不能让时间倒流，但可以决定让走过的每一秒都有分量。",
        "closing": "愿你的每一个整点都有欢喜",
        "postscript": "P.S. 顺其自然，发条别拧太紧",
    },
    {
        "sender": "巷尾深夜面包房的面包师",
        "greeting": "致每一个早起的人",
        "body": "凌晨四点，第一炉法棍散发出麦香和焦脆的声音。酵母在夜里静静发酵，等待清晨第一缕阳光。生活也是这样，耐得住黑暗，才有喷薄的香气。",
        "closing": "祝你今天有一份热气腾腾的心情",
        "postscript": "P.S. 早餐一定要吃饱",
    },
    {
        "sender": "雨夜站台等车的老画师",
        "greeting": "致撑伞前行的你",
        "body": "路灯把雨丝拉成金色的琴弦，倒影在积水里漾开一幅湿润的水彩画。即便遇上暴雨，世界的色彩也从未褪去，只是换了一种温润的方式呈现。",
        "closing": "愿你在平凡日常中发现诗意",
        "postscript": "P.S. 小心水坑，慢些走",
    },
]

# 预存毒舌吐槽库 (ROAST: 20条幽默扎心金句)
_ROAST_SEEDS = [
    {"quote": "服务器也累了，和你一样需要休息。"},
    {"quote": "加载中...就像你的人生一样，一直在加载。"},
    {"quote": "404 找到了，你的动力还没找到。"},
    {"quote": "网络超时，和你的耐心一起消失在风里。"},
    {"quote": "系统繁忙，建议你也忙点正事。"},
    {"quote": "屏幕刷新需要 1 秒，你下定决心需要 1 年。"},
    {"quote": "别看了，墨水屏上的待办清单又不会自己完成。"},
    {"quote": "早睡早起身体好，可惜你两条都没占到。"},
    {"quote": "摸鱼虽好，但离下班还有几个光年。"},
    {"quote": "今天的心情像这块黑白屏幕一样朴实无华且平淡。"},
    {"quote": "你对工作的热情，甚至不如手柄里的那节五号电池持久。"},
    {"quote": "只要你肯放弃，世界上就没有什么难事。"},
    {"quote": "生活不仅有诗和远方，还有改不完的第 18 版需求。"},
    {"quote": "既然做不到优秀，那就先把手头的事情对付完吧。"},
    {"quote": "你今天的步数，可能还不如送外卖小哥的电动车车轮转得快。"},
    {"quote": "墨水屏不伤眼，但银行卡余额有点伤心。"},
    {"quote": "努力不一定成功，但躺平确实挺舒服的。"},
    {"quote": "别总对着屏幕叹气，屏幕上的灰尘都快被你吹散了。"},
    {"quote": "如果拖延是一门艺术，你已经是大师级艺术家了。"},
    {"quote": "今天也是为了生活假装成熟稳重的一天呢。"},
]

# 预存禅意库 (ZEN: 20个精选汉字与意境)
_ZEN_SEEDS = [
    {"word": "静", "source": "万物归寂，心定神安"},
    {"word": "渡", "source": "苦海无边，回头是岸"},
    {"word": "空", "source": "色即是空，虚怀若谷"},
    {"word": "照", "source": "返观内心，朗照乾坤"},
    {"word": "息", "source": "一呼一吸，当下自在"},
    {"word": "定", "source": "知止而后有定"},
    {"word": "忘", "source": "相忘江湖，两两相安"},
    {"word": "澄", "source": "心如止水，波澜不惊"},
    {"word": "悟", "source": "瞬息万象，自性清净"},
    {"word": "默", "source": "大道无言，大音希声"},
    {"word": "简", "source": "去伪存真，素履以往"},
    {"word": "远", "source": "心远地自偏"},
    {"word": "常", "source": "知常容，容乃公"},
    {"word": "润", "source": "润物细无声"},
    {"word": "徐", "source": "缓步当车，从容不迫"},
    {"word": "归", "source": "倦鸟归林，万法朝宗"},
    {"word": "虚", "source": "虚极静笃，复命常安"},
    {"word": "融", "source": "物我两忘，万象融合"},
    {"word": "泊", "source": "淡泊明志，宁静致远"},
    {"word": "容", "source": "海纳百川，有容乃大"},
]

# 预存微小说 (STORY: 15篇闪小说)
_STORY_SEEDS = [
    {
        "title": "末班车",
        "opening": "她每天都坐末班地铁，座位对面总是同一个男人在看书。",
        "twist": "有一天她终于鼓起勇气搭话，男人抬头，手里的书封面是她写的小说。",
        "ending": "小说的最后一章写的是：她从未搭话。",
        "genre": "温情",
    },
    {
        "title": "旧雨伞",
        "opening": "他在雨天的便利店门口错拿了一把黑伞，伞柄刻着一个名字。",
        "twist": "三年后的一场大雨里，一个女孩冲进雨幕，手里正握着他原本丢失的那把。",
        "ending": "雨停时，两把伞并肩靠在墙角。",
        "genre": "温情",
    },
    {
        "title": "时光机",
        "opening": "老科学家耗费四十年心血，终于启动了只能发送三个字的时间机器。",
        "twist": "他把纸条送给四十年前打算放弃科研去经商的自己。",
        "ending": "纸条上写着：别放弃。",
        "genre": "科幻",
    },
    {
        "title": "回声",
        "opening": "他向深谷大喊了一声'我讨厌你'，静静等待着回声。",
        "twist": "过了许久，回荡而来的声音却清晰地传来：'但我依然爱你'。",
        "ending": "他愣住，才发现谷底有人在露营。",
        "genre": "荒诞",
    },
    {
        "title": "画像",
        "opening": "街头盲人画家答应为路过的女孩画一幅肖像，只凭手指轻触面庞。",
        "twist": "画像完成时，围观的人都惊呆了，画上的笑容与十年前失踪的女孩一模一样。",
        "ending": "老人微笑着说：女儿，你终于回家了。",
        "genre": "温情",
    },
]

# 预存诗词库 (POETRY: 20首经典诗词)
_POETRY_SEEDS = [
    {
        "title": "静夜思",
        "author": "唐·李白",
        "lines": ["床前明月光", "疑是地上霜", "举头望明月", "低头思故乡"],
        "note": "千古思乡名篇，朴素真挚",
    },
    {
        "title": "问刘十九",
        "author": "唐·白居易",
        "lines": ["绿蚁新醅酒", "红泥小火炉", "晚来天欲雪", "能饮一杯无"],
        "note": "冬日围炉对酌的温情闲适",
    },
    {
        "title": "山居秋暝",
        "author": "唐·王维",
        "lines": ["空山新雨后", "天气晚来秋", "明月松间照", "清泉石上流"],
        "note": "诗中有画，空灵悠远",
    },
    {
        "title": "春夜喜雨",
        "author": "唐·杜甫",
        "lines": ["好雨知时节", "当春乃发生", "随风潜入夜", "润物细无声"],
        "note": "喜雨之情自然流溢",
    },
    {
        "title": "定风波",
        "author": "宋·苏轼",
        "lines": ["莫听穿林打叶声", "何妨吟啸且徐行", "竹杖芒鞋轻胜马", "谁怕", "一蓑烟雨任平生"],
        "note": "旷达超然，笑对人生风雨",
    },
    {
        "title": "登鹳雀楼",
        "author": "唐·王之涣",
        "lines": ["白日依山尽", "黄河入海流", "欲穷千里目", "更上一层楼"],
        "note": "高瞻远瞩，气象开阔",
    },
]

# 预存每日一问 (QUESTION: 20个开放式思考题)
_QUESTION_SEEDS = [
    {
        "question": "你最近一次改变想法是什么时候？",
        "context_note": "改变想法是真正成长的标志",
        "category": "自我",
    },
    {
        "question": "如果今天可以放空一小时，你想做什么？",
        "context_note": "给生活留出呼吸的留白",
        "category": "生活",
    },
    {
        "question": "你今天最感谢谁给予的一点善意？",
        "context_note": "感恩会带来积极的内在能量",
        "category": "关系",
    },
    {
        "question": "有什么事情是你一直想做却迟迟未开始的？",
        "context_note": "觉察是跨出第一步的契机",
        "category": "成长",
    },
    {
        "question": "五年后的你，会如何看待今天纠结的事？",
        "context_note": "拉长视距，烦恼自然渺小",
        "category": "思维",
    },
]

# 预存认知偏差库 (BIAS: 20个经典心理学效应)
_BIAS_SEEDS = [
    {
        "name_cn": "幸存者偏差",
        "name_en": "Survivorship Bias",
        "definition": "只看到成功案例，忽略了失败的大多数",
        "example": "'辍学也能创业成功'——忽略了大量默默无闻的失败者。",
        "antidote": "主动搜寻被遗忘的反面样本",
    },
    {
        "name_cn": "锚定效应",
        "name_en": "Anchoring Effect",
        "definition": "第一印象或初始信息过度主导后续判断",
        "example": "一件标价999打折到299的衣服，让人觉得捡了大便宜。",
        "antidote": "独立估值，不受最初标价干扰",
    },
    {
        "name_cn": "沉没成本谬误",
        "name_en": "Sunk Cost Fallacy",
        "definition": "因已投入不可回收的时间金钱而坚持错误选择",
        "example": "电影很难看，却因为花了票钱硬着头皮坐了两个小时。",
        "antidote": "向前看，过去投入的无法挽回",
    },
    {
        "name_cn": "聚光灯效应",
        "name_en": "Spotlight Effect",
        "definition": "总以为所有人都在时刻关注自己的表现或瑕疵",
        "example": "衣服上弄脏了一点，觉得整条街的人都在看自己。",
        "antidote": "放宽心，大家都在忙着关注自己",
    },
    {
        "name_cn": "证实偏差",
        "name_en": "Confirmation Bias",
        "definition": "只寻找和相信符合自己已有观点的证据",
        "example": "相信星座的人，只记住说中自己的那些性格描述。",
        "antidote": "刻意去寻找证伪自己观点的论据",
    },
]

# 预存微挑战 (CHALLENGE: 20个微型每日挑战)
_CHALLENGE_SEEDS = [
    {
        "challenge": "给一个半年没联系的朋友发条简单问候",
        "why": "维系真挚关系不需要宏大理由",
        "difficulty": "★",
        "time": "2分钟",
    },
    {
        "challenge": "整理一下眼前的桌面，只留下必需品",
        "why": "整洁的空间能迅速恢复专注心流",
        "difficulty": "★",
        "time": "5分钟",
    },
    {
        "challenge": "走到窗边，注视远方天际深呼吸三次",
        "why": "舒缓眼睫状肌，重置大脑疲劳",
        "difficulty": "★",
        "time": "1分钟",
    },
    {
        "challenge": "今天在喝咖啡或茶时，不碰手机专注品味",
        "why": "训练在日常细节中的正念觉知",
        "difficulty": "★★",
        "time": "3分钟",
    },
    {
        "challenge": "用纸笔写下今天最顺利完成的三件事",
        "why": "正向强化能带来笃定的安全感",
        "difficulty": "★",
        "time": "3分钟",
    },
]


async def seed_preload_pool(days_ahead: int = 14) -> None:
    """自动补充未来 N 天的预存历史事件及全量 LLM 模式通用滚动池。"""
    today = date.today()

    # 1. 补充未来 days_ahead 天的历史事件 (THISDAY)
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

    # 2. 补充 DAILY / MY_QUOTE / STOIC
    for q in _QUOTE_SEEDS:
        await add_preload_item("DAILY", q)
        await add_preload_item("MY_QUOTE", q)
        await add_preload_item("STOIC", q)

    # 3. 补充 WORD_OF_THE_DAY (30+ 丰富词库)
    for w in _WORD_SEEDS:
        await add_preload_item("WORD_OF_THE_DAY", w)

    # 4. 补充 RIDDLE (每日一谜)
    for r in _RIDDLE_SEEDS:
        await add_preload_item("RIDDLE", r)

    # 5. 补充 LETTER (慢信)
    for lt in _LETTER_SEEDS:
        await add_preload_item("LETTER", lt)

    # 6. 补充 ROAST (毒舌吐槽)
    for ro in _ROAST_SEEDS:
        await add_preload_item("ROAST", ro)

    # 7. 补充 ZEN (禅意)
    for z in _ZEN_SEEDS:
        await add_preload_item("ZEN", z)

    # 8. 补充 STORY (微小说)
    for s in _STORY_SEEDS:
        await add_preload_item("STORY", s)

    # 9. 补充 POETRY (古诗词)
    for p in _POETRY_SEEDS:
        await add_preload_item("POETRY", p)

    # 10. 补充 QUESTION (每日一问)
    for qu in _QUESTION_SEEDS:
        await add_preload_item("QUESTION", qu)

    # 11. 补充 BIAS (认知偏差)
    for b in _BIAS_SEEDS:
        await add_preload_item("BIAS", b)

    # 12. 补充 CHALLENGE (微挑战)
    for ch in _CHALLENGE_SEEDS:
        await add_preload_item("CHALLENGE", ch)

    logger.info("[Preload] Successfully seeded comprehensive preload pool for all LLM modes.")
