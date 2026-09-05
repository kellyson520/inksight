"""
豆瓣电影精选与推荐数据服务 (Douban Movie Service)
提供豆瓣高分经典电影 (Top 250) 与实时热门榜单推荐。
排版对标微信读书样式：右侧竖版高清电影海报，左侧电影名、导演、豆瓣评分与高赞影评推荐理由。
【规范约束】：严格禁止 Emoji。
"""
from __future__ import annotations

import hashlib
import logging
import time
from typing import Any, Optional
import httpx

logger = logging.getLogger(__name__)

# 精选豆瓣传世高分经典电影库 (涵盖 Top250 顶流、科幻神作、治愈人生、悬疑经典等)
# 海报采用豆瓣高清影视图片 CDN (经过 1:1.45 黄金海报比例适配)，在墨水屏抖动算法下呈现极佳灰阶质感
DOUBAN_CLASSIC_MOVIES: list[dict[str, Any]] = [
    {
        "id": "db_001",
        "title": "肖申克的救赎",
        "title_en": "The Shawshank Redemption",
        "director": "弗兰克·德拉邦特",
        "year": "1994",
        "genre": "剧情 / 犯罪",
        "rating": "9.7",
        "rating_people": "285 万人评价",
        "rank_tag": "豆瓣电影 Top 250 · NO.1",
        "recommend_reason": "希望是美好的东西，也许是人间至善，而美好的东西永不消逝。二十年如一日的坚忍与信念，在暴雨雷鸣中张开双臂迎接真正的自由。",
        "quote": "恐惧囚禁灵魂，希望赐予自由。",
        "category": "TOP250",
        "cover_url": "https://img9.doubanio.com/view/photo/m_ratio_poster/public/p480747492.jpg",
        "cover_urls": ["https://img9.doubanio.com/view/photo/m_ratio_poster/public/p480747492.jpg", "https://img1.doubanio.com/view/subject/l/public/s1316831.jpg"],
    },
    {
        "id": "db_002",
        "title": "霸王别姬",
        "title_en": "Farewell My Concubine",
        "director": "陈凯歌",
        "year": "1993",
        "genre": "剧情 / 爱情 / 历史",
        "rating": "9.6",
        "rating_people": "210 万人评价",
        "rank_tag": "豆瓣电影 Top 250 · NO.2",
        "recommend_reason": "不疯魔不成活。半个世纪的时代波澜跌宕，舞台上的霸王与虞姬，化作中国影史难以逾越的悲壮绝响。",
        "quote": "说好的一辈子，差一年，差一个月，差一个时辰，都不是一辈子。",
        "category": "TOP250",
        "cover_url": "https://img3.doubanio.com/view/subject/l/public/s1441962.jpg",
    },
    {
        "id": "db_003",
        "title": "阿甘正传",
        "title_en": "Forrest Gump",
        "director": "罗伯特·泽米吉斯",
        "year": "1994",
        "genre": "剧情 / 爱情",
        "rating": "9.5",
        "rating_people": "218 万人评价",
        "rank_tag": "豆瓣电影 Top 250 · NO.3",
        "recommend_reason": "纯真与执着的奇迹。奔跑穿过时代的风雨，用最质朴的善良化解生活的莫测，羽毛飘荡处，是温暖而有力的生命之歌。",
        "quote": "生活就像一盒巧克力，你永远不知道下一块是什么味道。",
        "category": "TOP250",
        "cover_url": "https://img3.doubanio.com/view/subject/l/public/s1332822.jpg",
    },
    {
        "id": "db_004",
        "title": "星际穿越",
        "title_en": "Interstellar",
        "director": "克里斯托弗·诺兰",
        "year": "2014",
        "genre": "科幻 / 冒险 / 悬疑",
        "rating": "9.4",
        "rating_people": "195 万人评价",
        "rank_tag": "豆瓣电影 Top 250 · 科幻神作",
        "recommend_reason": "爱是唯一可以超越时间与空间维度的事物。黑洞视界边缘的壮丽苍凉与五维空间的书架，构筑了人类对浩瀚星海最浪漫的探索。",
        "quote": "不要温和地走进那个良夜，怒斥、怒斥光明的消逝。",
        "category": "SCI_FI",
        "cover_url": "https://img9.doubanio.com/view/photo/m_ratio_poster/public/p2614988097.jpg",
    },
    {
        "id": "db_005",
        "title": "千与千寻",
        "title_en": "Spirited Away",
        "director": "宫崎骏",
        "year": "2001",
        "genre": "动画 / 奇幻 / 冒险",
        "rating": "9.4",
        "rating_people": "225 万人评价",
        "rank_tag": "豆瓣电影 Top 250 · 动画殿堂",
        "recommend_reason": "不要忘记自己的名字，不要在欲望中迷失自我。宫崎骏笔下充满哲思的奇幻汤屋，温暖抚慰每一个步入成人世界的灵魂。",
        "quote": "人生就是一列开往坟墓的列车，路途上会有很多站，很难有人自始至终陪你走完。",
        "category": "HEALING",
        "cover_url": "https://img9.doubanio.com/view/photo/m_ratio_poster/public/p2557573348.jpg",
    },
    {
        "id": "db_006",
        "title": "泰坦尼克号",
        "title_en": "Titanic",
        "director": "詹姆斯·卡梅隆",
        "year": "1997",
        "genre": "剧情 / 爱情 / 灾难",
        "rating": "9.5",
        "rating_people": "210 万人评价",
        "rank_tag": "豆瓣电影 Top 250 · 爱情经典",
        "recommend_reason": "冰冷北大西洋深处的不朽绝唱。跨越阶级藩篱的纯粹爱恋与危难之际人性的光辉，造就世界影史永恒的丰碑。",
        "quote": "赢得船票是我一生中最幸运的事，它让我遇见了你。",
        "category": "TOP250",
        "cover_url": "https://img9.doubanio.com/view/photo/m_ratio_poster/public/p457760035.jpg",
    },
    {
        "id": "db_007",
        "title": "盗梦空间",
        "title_en": "Inception",
        "director": "克里斯托弗·诺兰",
        "year": "2010",
        "genre": "动作 / 科幻 / 悬疑",
        "rating": "9.4",
        "rating_people": "208 万人评价",
        "rank_tag": "豆瓣电影 Top 250 · 悬疑神作",
        "recommend_reason": "梦境与现实的多重交织，思维植入的精密架构。旋转不倒的陀螺，成为世界影史最令人着迷的开放式结局。",
        "quote": "最坚韧的寄生虫是什么？是想法。一个想法能改变世界。",
        "category": "SCI_FI",
        "cover_url": "https://img9.doubanio.com/view/photo/m_ratio_poster/public/p513344864.jpg",
    },
    {
        "id": "db_008",
        "title": "楚门的世界",
        "title_en": "The Truman Show",
        "director": "彼得·威尔",
        "year": "1998",
        "genre": "剧情 / 科幻",
        "rating": "9.4",
        "rating_people": "172 万人评价",
        "rank_tag": "豆瓣电影 Top 250 · 哲学启示",
        "recommend_reason": "三十年的巨大真人秀，虚假世界的尽头是一扇通往真实的门。面对风暴与未知，他微笑着鞠躬致意，迈向属于自己的真实人生。",
        "quote": "假如再碰不见你，祝你早安、午安，还有晚安。",
        "category": "TOP250",
        "cover_url": "https://img9.doubanio.com/view/photo/m_ratio_poster/public/p479682972.jpg",
    },
    {
        "id": "db_009",
        "title": "这个杀手不太冷",
        "title_en": "Léon: The Professional",
        "director": "吕克·贝松",
        "year": "1994",
        "genre": "剧情 / 动作 / 犯罪",
        "rating": "9.4",
        "rating_people": "230 万人评价",
        "rank_tag": "豆瓣电影 Top 250 · 经典名作",
        "recommend_reason": "一盆无根的银皇后盆栽，一个喝牛奶的职业杀手，一个倔强绝望的小女孩。孤独灵魂之间的相互救赎与无声守护。",
        "quote": "生活总是这么痛苦吗？还是只有童年是这样？——总是如此。",
        "category": "TOP250",
        "cover_url": "https://img9.doubanio.com/view/photo/m_ratio_poster/public/p511118051.jpg",
    },
    {
        "id": "db_010",
        "title": "忠犬八公的故事",
        "title_en": "Hachi: A Dog's Tale",
        "director": "莱塞·霍尔斯道姆",
        "year": "2009",
        "genre": "剧情",
        "rating": "9.4",
        "rating_people": "145 万人评价",
        "rank_tag": "豆瓣电影 Top 250 · 治愈感动",
        "recommend_reason": "火车站台前漫长十载的守候，春夏秋冬轮回不改的等待。用一生的忠诚与思念，诠释爱与陪伴的终极意义。",
        "quote": "它们以为你永远不会回来了，但你一直在那里等他。",
        "category": "HEALING",
        "cover_url": "https://img9.doubanio.com/view/photo/m_ratio_poster/public/p524964016.jpg",
    },
]

for _movie in DOUBAN_CLASSIC_MOVIES:
    _primary = str(_movie.get("cover_url") or "")
    _existing = _movie.get("cover_urls") or []
    _movie["cover_urls"] = []
    for _url in [_primary, *_existing]:
        if _url and _url not in _movie["cover_urls"]:
            _movie["cover_urls"].append(_url)


class DoubanMovieService:
    """豆瓣电影数据服务（支持经典库轮播与实时榜单拉取）。"""

    def __init__(self) -> None:
        self._movies: list[dict[str, Any]] = DOUBAN_CLASSIC_MOVIES
        self._cache_online: dict[str, list[dict[str, Any]]] = {}
        self._cache_time: dict[str, float] = {}

    def get_movies_by_category(self, category: str = "ALL") -> list[dict[str, Any]]:
        """按分类筛选电影。"""
        cat = category.strip().upper()
        if not cat or cat == "ALL":
            return list(self._movies)
        return [m for m in self._movies if m.get("category") == cat]

    async def fetch_douban_online_items(self, collection_type: str = "movie_top250") -> list[dict[str, Any]]:
        """从豆瓣官方移动端 Rexxar 接口安全拉取精选榜单。"""
        now = time.time()
        if collection_type in self._cache_online and (now - self._cache_time.get(collection_type, 0) < 1800):
            return self._cache_online[collection_type]

        url = f"https://m.douban.com/rexxar/api/v2/subject_collection/{collection_type}/items?count=15"
        headers = {
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148",
            "Referer": "https://m.douban.com/movie",
        }
        res: list[dict[str, Any]] = []
        try:
            async with httpx.AsyncClient(timeout=4.5, follow_redirects=True) as client:
                resp = await client.get(url, headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    items = data.get("subject_collection_items", [])
                    for idx, it in enumerate(items):
                        title = str(it.get("title") or "")
                        if not title:
                            continue
                        rating_val = str(it.get("rating", {}).get("value") or "9.0")
                        rating_cnt = it.get("rating", {}).get("count")
                        people_str = f"{rating_cnt:,}人评价" if rating_cnt else "高分推荐"
                        cover = it.get("cover", {}).get("url") or (it.get("photos") or [None])[0] or ""
                        info_str = str(it.get("info") or "")
                        
                        comment = ""
                        if it.get("comment"):
                            comment = str(it.get("comment"))
                        elif it.get("description"):
                            comment = str(it.get("description"))

                        res.append({
                            "id": f"online_{idx + 1}",
                            "title": title,
                            "director": info_str.split("/")[0].strip() if "/" in info_str else info_str,
                            "year": info_str.split("/")[-1].strip() if "/" in info_str else "",
                            "genre": "高分佳作",
                            "rating": rating_val,
                            "rating_people": people_str,
                            "rank_tag": f"豆瓣电影 · Top {idx + 1}",
                            "recommend_reason": comment or f"豆瓣高分影视精选推荐，深刻探讨人性与生活，备受百万影迷推崇。",
                            "quote": f"好电影如同一盏灯，照亮我们内心的角落。",
                            "category": "HOT",
                            "cover_url": cover,
                            "cover_urls": [cover] if cover else [],
                        })
                    if res:
                        self._cache_online[collection_type] = res
                        self._cache_time[collection_type] = now
                        return res
        except Exception as e:
            logger.debug("[DoubanMovieService] Failed to fetch online douban items: %s", e)

        return []

    def get_recommended_movie(
        self,
        category: str = "ALL",
        movie_id: Optional[str] = None,
        seed: Optional[str] = None,
    ) -> dict[str, Any]:
        """获取一部精选电影，输出对齐微信读书的墨水屏排版数据字典。"""
        candidates = self.get_movies_by_category(category)
        if not candidates:
            candidates = list(self._movies)

        selected: dict[str, Any] = candidates[0]
        if movie_id:
            for m in candidates:
                if str(m.get("id")) == str(movie_id):
                    selected = m
                    break
        elif seed:
            idx = int(hashlib.md5(seed.encode("utf-8")).hexdigest(), 16) % len(candidates)
            selected = candidates[idx]

        title = selected.get("title", "肖申克的救赎")
        director = selected.get("director", "弗兰克·德拉邦特")
        year = selected.get("year", "1994")
        genre = selected.get("genre", "剧情")
        rating = selected.get("rating", "9.7")
        people = selected.get("rating_people", "280 万人评价")
        rank_tag = selected.get("rank_tag", "豆瓣电影 Top 250 · NO.1")
        reason = selected.get("recommend_reason", "希望是美好的东西，也许是人间至善，而美好的东西永不消逝。")
        quote = selected.get("quote", "恐惧囚禁灵魂，希望赐予自由。")
        cover_url = selected.get("cover_url", "")

        director_line = f"{director} 执导 · {year} · {genre}"
        rating_label = f"豆瓣 {rating} 分"

        return {
            "id": selected.get("id", "db_001"),
            "title": title,
            "title_bracketed": f"《{title}》",
            "director": director,
            "year": year,
            "genre": genre,
            "director_line": director_line,
            "rating": rating,
            "rating_label": rating_label,
            "rating_people": people,
            "rank_tag": rank_tag,
            "recommend_reason": reason,
            "quote": quote,
            "cover_url": cover_url,
            "cover_urls": list(selected.get("cover_urls") or [cover_url]),
            "update_time": "精选",
            "footer_label": "豆瓣电影 · 影史精选",
            "footer_quote": quote,
        }


douban_movie_service = DoubanMovieService()
