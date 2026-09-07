import pytest
from core.mihomo_service import (
    MihomoService,
    _format_bytes,
    _parse_userinfo_header,
    mihomo_service,
)
from core.mode_catalog import BUILTIN_CATALOG, builtin_catalog_map
from core.pipeline import generate_and_render
from core.wechat_read_service import wechat_read_service
from core.douban_movie_service import douban_movie_service


def test_format_bytes():
    assert _format_bytes(0) == "0 B"
    assert _format_bytes(-10) == "0 B"
    assert _format_bytes(1024) == "1.0 KB"
    assert _format_bytes(1024 * 1024 * 50) == "50.0 MB"
    assert _format_bytes(1024 * 1024 * 1024 * 205) == "205.0 GB"
    assert _format_bytes(1024 * 1024 * 1024 * 1024 * 2) == "2.00 TB"
    assert _format_bytes("invalid") == "0 B"


def test_parse_userinfo_header():
    header = "upload=1073741824; download=10737418240; total=107374182400; expire=1818746512"
    parsed = _parse_userinfo_header(header)
    assert parsed["upload"] == 1073741824
    assert parsed["download"] == 10737418240
    assert parsed["total"] == 107374182400
    assert parsed["expire"] == 1818746512


@pytest.mark.asyncio
async def test_mihomo_service_dashboard_data():
    data = await mihomo_service.get_dashboard_data()
    assert data is not None
    assert "total_str" in data
    assert "used_str" in data
    assert "remaining_str" in data
    assert "expire_str" in data
    assert "days_left_badge" in data
    assert "progress_percent" in data
    assert 0 <= data["progress_percent"] <= 100


@pytest.mark.asyncio
async def test_mihomo_sub_mode_render():
    for lang in ["zh", "en"]:
        img, content = await generate_and_render(
            persona="MIHOMO_SUB",
            config={"mode_language": lang},
            date_ctx={"time_str": "12:00", "date_str": "09/07"},
            weather={"weather_str": "晴", "weather_code": 0},
            battery_pct=95.0,
            screen_w=400,
            screen_h=300,
            colors=4,
        )
        assert img.size == (400, 300)
        assert content is not None
        assert "remaining_str" in content
        assert "progress_percent" in content


def test_catalog_categories_valid():
    """验证所有模式分类符合 core | more | custom 规范，杜绝前端过滤丢失。"""
    cat_map = builtin_catalog_map()
    for mid in ["GITHUB_PULSE", "ELEMENT_DAY", "XKCD_COMIC", "TECH_RADAR", "MIHOMO_SUB"]:
        assert mid in cat_map, f"Mode {mid} missing in BUILTIN_CATALOG"
        item = cat_map[mid]
        assert item.category in ("core", "more", "custom"), (
            f"Mode {mid} has invalid category {item.category}, must be core, more, or custom"
        )


@pytest.mark.asyncio
async def test_wechat_read_dynamic_fetch():
    """验证微信读书可动态拉取线上书单并降级保护。"""
    online_books = await wechat_read_service.fetch_online_books("ALL")
    assert isinstance(online_books, list)
    # 若联网正常，拉取结果不为空
    if online_books:
        book = online_books[0]
        assert book.get("title")
        assert book.get("cover_url")
        assert "weread.qq.com" in book.get("cover_url")

    # 验证集成调用正常
    res = await wechat_read_service.get_online_or_curated_book(category="ALL", seed="device123")
    assert res is not None
    assert "cover_url" in res
    assert "recommend_reason" in res


@pytest.mark.asyncio
async def test_douban_movie_dynamic_fetch():
    """验证豆瓣电影可动态拉取 Top250 与热门榜单。"""
    online_movies = await douban_movie_service.fetch_douban_online_items("movie_top250")
    assert isinstance(online_movies, list)
    if online_movies:
        movie = online_movies[0]
        assert movie.get("title")
        assert movie.get("cover_url")
        assert "doubanio.com" in movie.get("cover_url")
        assert "img9.doubanio.com" not in movie.get("cover_url")
        assert "Top 250" in movie.get("rank_tag")
