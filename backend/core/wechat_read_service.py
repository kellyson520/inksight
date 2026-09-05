"""
微信读书推荐数据服务 (WeChat Read Service)
提供精选高分神作与热门榜单好书推荐，输出书名、作者、分类、评分、在读人数、推荐理由与封面图片。
【排版规范】：严格禁止 Emoji。
"""
from __future__ import annotations

import hashlib
import logging
import time
from typing import Any

logger = logging.getLogger(__name__)

# 微信读书官方 CDN 或高可用稳定书封 CDN
# 尺寸比例约 1:1.45 (典型书籍开本)，灰度墨水屏抖动显示效果极佳
WECHAT_READ_BOOKS: list[dict[str, Any]] = [
    {
        "id": "wr_001",
        "title": "明朝那些事儿",
        "author": "当年明月",
        "category": "HISTORY",
        "category_name": "历史社科",
        "rating": "94.8%",
        "rating_label": "神作 · 94.8% 推荐",
        "reading_count": "4.1 万人在读",
        "rank_tag": "微信读书 · 总榜 Top 1",
        "recommend_reason": "以幽默生动的现代视角重现大明三百年风云。写历史也是写人性与权谋，千万读者心中的通俗历史第一书。",
        "quote": "成功只有一个，按照自己的方式去度过人生。",
        "cover_url": "https://wfqqreader-1252317822.image.myqcloud.com/cover/786/842786/t6_842786.jpg",
    },
    {
        "id": "wr_002",
        "title": "置身事内：中国政府与经济发展",
        "author": "兰小欢",
        "category": "BUSINESS",
        "category_name": "商业财经",
        "rating": "95.2%",
        "rating_label": "神作 · 95.2% 推荐",
        "reading_count": "2.8 万人在读",
        "rank_tag": "微信读书 · 经济榜 Top 1",
        "recommend_reason": "理解中国经济微观机制与地方政府决策的必读书，通俗透彻，兼具严谨学理与现实温度。",
        "quote": "生活过得好一点，比大多数宏大叙事都重要。",
        "cover_url": "https://wfqqreader-1252317822.image.myqcloud.com/cover/571/36531571/t6_36531571.jpg",
    },
    {
        "id": "wr_003",
        "title": "三体全集",
        "author": "刘慈欣",
        "category": "LITERATURE",
        "category_name": "科幻文学",
        "rating": "95.8%",
        "rating_label": "神作 · 95.8% 推荐",
        "reading_count": "5.6 万人在读",
        "rank_tag": "微信读书 · 科幻榜 Top 1",
        "recommend_reason": "中国科幻文学的巍峨丰碑。宇宙社会学的冷酷推演与文明兴衰的壮阔画卷，给岁月以文明。",
        "quote": "弱小和无知不是生存的障碍，傲慢才是。",
        "cover_url": "https://wfqqreader-1252317822.image.myqcloud.com/cover/354/22588354/t6_22588354.jpg",
    },
    {
        "id": "wr_004",
        "title": "蛤蟆先生去看心理医生",
        "author": "罗伯特·戴博德",
        "category": "GROWTH",
        "category_name": "心理认知",
        "rating": "91.2%",
        "rating_label": "好评 · 91.2% 推荐",
        "reading_count": "3.5 万人在读",
        "rank_tag": "微信读书 · 心理榜 Top 1",
        "recommend_reason": "借童话外壳讲述深邃的心理咨询历程，引导我们学会理解情绪、直面脆弱，完成自我救赎与重塑。",
        "quote": "没有一种批判比自我批判更强烈，也没有一个法官比我们自己更苛刻。",
        "cover_url": "https://wfqqreader-1252317822.image.myqcloud.com/cover/892/33560892/t6_33560892.jpg",
    },
    {
        "id": "wr_005",
        "title": "被讨厌的勇气",
        "author": "岸见一郎 / 古贺史健",
        "category": "GROWTH",
        "category_name": "哲学成长",
        "rating": "92.6%",
        "rating_label": "神作 · 92.6% 推荐",
        "reading_count": "3.9 万人在读",
        "rank_tag": "微信读书 · 哲学榜 Top 1",
        "recommend_reason": "阿德勒个体心理学的现代对话演绎。课题分离、摆脱认可欲求，活在当下拥有自由人生的底气。",
        "quote": "所谓自由，就是被别人讨厌。",
        "cover_url": "https://wfqqreader-1252317822.image.myqcloud.com/cover/513/853513/t6_853513.jpg",
    },
    {
        "id": "wr_006",
        "title": "百年孤独",
        "author": "加西亚·马尔克斯",
        "category": "LITERATURE",
        "category_name": "世界名著",
        "rating": "93.4%",
        "rating_label": "神作 · 93.4% 推荐",
        "reading_count": "2.2 万人在读",
        "rank_tag": "微信读书 · 名著榜 Top 2",
        "recommend_reason": "魔幻现实主义的传世巨作。布恩迪亚家族七代人在马孔多小镇的百年沧桑，揭示人类深沉的孤独宿命。",
        "quote": "生命中曾经有过的所有灿烂，终究都需要用寂寞来偿还。",
        "cover_url": "https://wfqqreader-1252317822.image.myqcloud.com/cover/836/834836/t6_834836.jpg",
    },
    {
        "id": "wr_007",
        "title": "纳瓦尔宝典",
        "author": "埃里克·乔根森",
        "category": "BUSINESS",
        "category_name": "商业财富",
        "rating": "92.0%",
        "rating_label": "好评 · 92.0% 推荐",
        "reading_count": "3.1 万人在读",
        "rank_tag": "微信读书 · 财富榜 Top 2",
        "recommend_reason": "硅谷投资人纳瓦尔的智慧合集。阐述如何依靠专长与杠杆创造财富，以及如何获取内心的平静与幸福。",
        "quote": "用头脑赚钱，而不是用时间赚钱。",
        "cover_url": "https://wfqqreader-1252317822.image.myqcloud.com/cover/805/37450805/t6_37450805.jpg",
    },
    {
        "id": "wr_008",
        "title": "人类简史：从动物到上帝",
        "author": "尤瓦尔·赫拉利",
        "category": "HISTORY",
        "category_name": "历史社科",
        "rating": "93.8%",
        "rating_label": "神作 · 93.8% 推荐",
        "reading_count": "2.5 万人在读",
        "rank_tag": "微信读书 · 历史榜 Top 2",
        "recommend_reason": "宏大跨学科视角理清智人进化跃迁全过程。认知革命、农业革命与虚构故事如何塑造现代人类文明。",
        "quote": "演化从来不看个体的幸福，它只看物种的延续。",
        "cover_url": "https://wfqqreader-1252317822.image.myqcloud.com/cover/545/802545/t6_802545.jpg",
    },
    {
        "id": "wr_009",
        "title": "额尔古纳河右岸",
        "author": "迟子建",
        "category": "LITERATURE",
        "category_name": "当代文学",
        "rating": "94.5%",
        "rating_label": "神作 · 94.5% 推荐",
        "reading_count": "3.0 万人在读",
        "rank_tag": "微信读书 · 文学榜 Top 1",
        "recommend_reason": "鄂温克族最后一任酋长女人的百年自述。展现大兴安岭深处人与自然的生死契约与民族挽歌。",
        "quote": "我是雨和雪的老朋友了，我也看够了它们的面孔。",
        "cover_url": "https://wfqqreader-1252317822.image.myqcloud.com/cover/571/3421571/t6_3421571.jpg",
    },
    {
        "id": "wr_010",
        "title": "金钱心理学",
        "author": "摩根·豪泽尔",
        "category": "BUSINESS",
        "category_name": "商业理财",
        "rating": "91.5%",
        "rating_label": "好评 · 91.5% 推荐",
        "reading_count": "2.9 万人在读",
        "rank_tag": "微信读书 · 理财榜 Top 3",
        "recommend_reason": "关于财富、贪婪与幸福的19个短篇故事。理财的核心不是冷冰冰的数字，而是对自我心理行为的驾驭。",
        "quote": "最高形式的富有，是每天清晨醒来都能对自己说：今天我可以做任何我想做的事。",
        "cover_url": "https://wfqqreader-1252317822.image.myqcloud.com/cover/572/38531572/t6_38531572.jpg",
    },
    {
        "id": "wr_011",
        "title": "活着",
        "author": "余华",
        "category": "LITERATURE",
        "category_name": "中国文学",
        "rating": "94.9%",
        "rating_label": "神作 · 94.9% 推荐",
        "reading_count": "4.8 万人在读",
        "rank_tag": "微信读书 · 畅销总榜",
        "recommend_reason": "福贵饱经风霜的苦难一生，深刻揭示人为了活着本身而活着的坚韧力量，当代文学必读殿堂作。",
        "quote": "人是为活着本身而活着的，而不是为了活着之外的任何事物所活着。",
        "cover_url": "https://wfqqreader-1252317822.image.myqcloud.com/cover/833/834833/t6_834833.jpg",
    },
    {
        "id": "wr_012",
        "title": "认知觉醒：开启自我改变的原动力",
        "author": "周岭",
        "category": "GROWTH",
        "category_name": "个人成长",
        "rating": "91.8%",
        "rating_label": "好评 · 91.8% 推荐",
        "reading_count": "3.3 万人在读",
        "rank_tag": "微信读书 · 个人成长榜",
        "recommend_reason": "用脑科学与心理学剖析焦虑、拖延与专注力缺失的深层根源，提供清晰具体的行动跃迁框架。",
        "quote": "焦虑的原因就两个：想得太多，做得太少。",
        "cover_url": "https://wfqqreader-1252317822.image.myqcloud.com/cover/248/34537248/t6_34537248.jpg",
    },
]

CATEGORIES = [
    {"key": "ALL", "name": "精选好书"},
    {"key": "LITERATURE", "name": "文学小说"},
    {"key": "HISTORY", "name": "历史社科"},
    {"key": "BUSINESS", "name": "商业财经"},
    {"key": "GROWTH", "name": "认知成长"},
]


class WeChatReadService:
    """微信读书数据与推荐服务。"""

    def __init__(self) -> None:
        self._books = WECHAT_READ_BOOKS

    def list_categories(self) -> list[dict[str, str]]:
        return CATEGORIES

    def get_books_by_category(self, category: str = "ALL") -> list[dict[str, Any]]:
        cat = category.strip().upper()
        if not cat or cat == "ALL":
            return self._books
        filtered = [b for b in self._books if b.get("category", "").upper() == cat]
        return filtered or self._books

    def get_recommended_book(
        self,
        category: str = "ALL",
        book_id: str | None = None,
        seed: str | None = None,
    ) -> dict[str, Any]:
        """按分类或指定ID推荐一本微信读书好书。"""
        books = self.get_books_by_category(category)

        # 优先匹配特定 ID
        if book_id:
            for b in self._books:
                if b["id"] == book_id or b["title"] == book_id:
                    return self._format_book(b)

        # 根据种子确定索引，确保周期内稳定或随天更新
        if seed:
            idx = int(hashlib.md5(seed.encode("utf-8")).hexdigest(), 16) % len(books)
        else:
            # 默认按当前时间戳每小时或每刷新切换
            # 用当天天数加小时作为扰动
            t = time.localtime()
            idx = (t.tm_yday * 24 + t.tm_hour) % len(books)

        chosen = books[idx]
        return self._format_book(chosen)

    def _format_book(self, book: dict[str, Any]) -> dict[str, Any]:
        res = dict(book)
        res["title_bracketed"] = f"《{book['title']}》"
        res["author_category"] = f"{book['author']} · {book.get('category_name', '图书')}"
        res["update_time"] = time.strftime("%H:%M")
        res["status_text"] = "微信读书精选"
        return res


# 全局单例
wechat_read_service = WeChatReadService()
