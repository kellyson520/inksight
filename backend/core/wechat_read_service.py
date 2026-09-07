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
import httpx

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
        "cover_url": "https://cdn.weread.qq.com/weread/cover/97/yuewen_822995/t6_yuewen_8229951695023669.jpg",
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
        "cover_url": "https://cdn.weread.qq.com/weread/cover/52/YueWen_40055543/t6_YueWen_40055543.jpg",
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
        "cover_url": "https://cdn.weread.qq.com/weread/cover/80/yuewen_695233/t6_yuewen_6952331784884457.jpg",
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
        "cover_url": "https://cdn.weread.qq.com/weread/cover/81/YueWen_35551088/t6_YueWen_35551088.jpg",
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
        "cover_url": "https://wfqqreader-1252317822.image.myqcloud.com/cover/385/25615385/t6_25615385.jpg",
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
        "cover_url": "https://cdn.weread.qq.com/weread/cover/49/yuewen_935536/t6_yuewen_9355361682243599.jpg",
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
        "cover_url": "https://cdn.weread.qq.com/weread/cover/89/YueWen_44026191/t6_YueWen_44026191.jpg",
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
        "cover_url": "https://cdn.weread.qq.com/weread/cover/37/YueWen_855812/t6_YueWen_855812.jpg",
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
        "cover_url": "https://cdn.weread.qq.com/outpic/407/3004054407.jpg",
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
        "cover_url": "https://cdn.weread.qq.com/weread/cover/31/cpplatform_fx1z5bkdgmbwqoatwezcxp/t6_cpplatform_fx1z5bkdgmbwqoatwezcxp1778466805.jpg",
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
        "cover_url": "https://cdn.weread.qq.com/weread/cover/1/yuewen_834464/t6_yuewen_8344641758521403.jpg",
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
        "cover_url": "https://cdn.weread.qq.com/weread/cover/86/YueWen_33628204/t6_YueWen_33628204.jpg",
    },
]

# 远程书封候选源：主源失效时交由 MediaFetcher 自动切换。
_WECHAT_COVER_FALLBACKS: dict[str, list[str]] = {
    "wr_001": [
        "https://cdn.weread.qq.com/weread/cover/97/yuewen_822995/s_yuewen_8229951695023669.jpg",
        "https://wfqqreader-1252317822.image.myqcloud.com/cover/786/842786/t6_842786.jpg",
    ],
    "wr_002": [
        "https://cdn.weread.qq.com/weread/cover/52/YueWen_40055543/s_YueWen_40055543.jpg",
        "https://wfqqreader-1252317822.image.myqcloud.com/cover/571/36531571/t6_36531571.jpg",
    ],
    "wr_003": [
        "https://cdn.weread.qq.com/weread/cover/80/yuewen_695233/s_yuewen_6952331784884457.jpg",
        "https://wfqqreader-1252317822.image.myqcloud.com/cover/354/22588354/t6_22588354.jpg",
    ],
    "wr_004": [
        "https://cdn.weread.qq.com/weread/cover/81/YueWen_35551088/s_YueWen_35551088.jpg",
    ],
    "wr_005": [
        "https://wfqqreader-1252317822.image.myqcloud.com/cover/385/25615385/s_25615385.jpg",
    ],
    "wr_006": [
        "https://cdn.weread.qq.com/weread/cover/49/yuewen_935536/s_yuewen_9355361682243599.jpg",
    ],
    "wr_007": [
        "https://cdn.weread.qq.com/weread/cover/89/YueWen_44026191/s_YueWen_44026191.jpg",
    ],
    "wr_008": [
        "https://cdn.weread.qq.com/weread/cover/37/YueWen_855812/s_YueWen_855812.jpg",
    ],
    "wr_009": [
        "https://cdn.weread.qq.com/weread/cover/56/cpplatform_pxdcpye4umtlndzeqdkyws/t6_cpplatform_pxdcpye4umtlndzeqdkyws1755678528.jpg",
    ],
    "wr_010": [
        "https://cdn.weread.qq.com/weread/cover/31/cpplatform_fx1z5bkdgmbwqoatwezcxp/s_cpplatform_fx1z5bkdgmbwqoatwezcxp1778466805.jpg",
    ],
    "wr_011": [
        "https://cdn.weread.qq.com/weread/cover/1/yuewen_834464/s_yuewen_8344641758521403.jpg",
    ],
    "wr_012": [
        "https://cdn.weread.qq.com/weread/cover/86/YueWen_33628204/s_YueWen_33628204.jpg",
    ],
}
for _book in WECHAT_READ_BOOKS:
    _primary = str(_book.get("cover_url") or "")
    _book["cover_urls"] = []
    for _url in [_primary, *_WECHAT_COVER_FALLBACKS.get(_book["id"], [])]:
        if _url and _url not in _book["cover_urls"]:
            _book["cover_urls"].append(_url)

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
        self._cache_online: dict[str, list[dict[str, Any]]] = {}
        self._cache_time: dict[str, float] = {}

    def list_categories(self) -> list[dict[str, str]]:
        return CATEGORIES

    def get_books_by_category(self, category: str = "ALL") -> list[dict[str, Any]]:
        cat = category.strip().upper()
        if not cat or cat == "ALL":
            return self._books
        filtered = [b for b in self._books if b.get("category", "").upper() == cat]
        return filtered or self._books

    async def fetch_online_books(self, category: str = "ALL") -> list[dict[str, Any]]:
        """从微信读书官方公开检索与趋势接口动态获取实时书单。"""
        cat = category.strip().upper() or "ALL"
        now = time.time()
        if cat in self._cache_online and (now - self._cache_time.get(cat, 0) < 1800):
            return self._cache_online[cat]

        query_map = {
            "ALL": "微信读书神作",
            "LITERATURE": "名著经典",
            "HISTORY": "历史经典",
            "BUSINESS": "商业经典",
            "GROWTH": "个人成长",
        }
        kw = query_map.get(cat, "微信读书精选")
        url = f"https://weread.qq.com/web/search/global?keyword={kw}&maxIdx=0"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://weread.qq.com/",
        }

        category_labels = {
            "ALL": "精选好书",
            "LITERATURE": "文学名著",
            "HISTORY": "历史社科",
            "BUSINESS": "商业财经",
            "GROWTH": "认知成长",
        }
        cat_label = category_labels.get(cat, "深度阅读")

        res: list[dict[str, Any]] = []
        try:
            async with httpx.AsyncClient(timeout=4.5, follow_redirects=True) as client:
                resp = await client.get(url, headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    books = data.get("books", [])
                    for idx, item in enumerate(books):
                        info = item.get("bookInfo", {})
                        title = str(info.get("title") or "").strip()
                        if not title:
                            continue
                        author = str(info.get("author") or "精选作者").strip()
                        cover = str(info.get("cover") or "").strip()
                        if not cover:
                            continue
                        # 将缩略小图升级为 t6 高清竖版大图
                        t6_cover = cover.replace("/s_", "/t6_")
                        intro = str(info.get("intro") or item.get("searchReason") or f"微信读书热门好书推荐，汇聚百万读者深度思考与精选批注。").strip()
                        # 过滤多余换行与空格
                        intro = " ".join(intro.split())
                        if len(intro) > 90:
                            intro = intro[:88] + "..."

                        reading_cnt = info.get("readingCount")
                        reading_str = f"{max(1, reading_cnt // 10000)} 万人在读" if reading_cnt else "万人热读"
                        rating_val = info.get("star")
                        rating_str = f"{rating_val}%" if rating_val else "94.5%"

                        res.append({
                            "id": f"wr_online_{idx + 1}",
                            "title": title,
                            "author": author,
                            "category": cat,
                            "category_name": cat_label,
                            "rating": rating_str,
                            "rating_label": f"神作 · {rating_str} 推荐",
                            "reading_count": reading_str,
                            "rank_tag": f"微信读书 · {cat_label} Top {idx + 1}",
                            "recommend_reason": intro,
                            "quote": f"阅读是心灵的栖息地，在文字中遇见更辽阔的自己。",
                            "cover_url": t6_cover,
                            "cover_urls": [t6_cover, cover],
                        })
                    if res:
                        self._cache_online[cat] = res
                        self._cache_time[cat] = now
                        return res
        except Exception as err:
            logger.debug("[WeChatReadService] Failed to fetch online weread books: %s", err)

        return []

    async def get_online_or_curated_book(
        self,
        category: str = "ALL",
        book_id: str | None = None,
        seed: str | None = None,
    ) -> dict[str, Any]:
        """优先动态拉取微信读书线上热读与神作，失败平滑降级至本地典藏库。"""
        if book_id:
            return self.get_recommended_book(category=category, book_id=book_id, seed=seed)

        try:
            online_books = await self.fetch_online_books(category)
            if online_books:
                if seed:
                    idx = int(hashlib.md5(seed.encode("utf-8")).hexdigest(), 16) % len(online_books)
                else:
                    t = time.localtime()
                    idx = (t.tm_yday * 24 + t.tm_hour) % len(online_books)
                return self._format_book(online_books[idx])
        except Exception as exc:
            logger.debug("[WeChatReadService] Online fetch fell back to curated books: %s", exc)

        return self.get_recommended_book(category=category, book_id=book_id, seed=seed)

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
        res["cover_urls"] = list(book.get("cover_urls") or [book.get("cover_url", "")])
        res["title_bracketed"] = f"《{book['title']}》"
        res["author_category"] = f"{book['author']} · {book.get('category_name', '图书')}"
        res["update_time"] = time.strftime("%H:%M")
        res["status_text"] = "微信读书精选"
        return res


# 全局单例
wechat_read_service = WeChatReadService()
