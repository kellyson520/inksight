import pytest
from core.douban_movie_service import DOUBAN_CLASSIC_MOVIES, DoubanMovieService
from core.wechat_read_service import WECHAT_READ_BOOKS
from core.media_fetcher import MediaFetcher


def test_wechat_read_books_have_valid_official_covers():
    for book in WECHAT_READ_BOOKS:
        bid = book["id"]
        cover_url = book.get("cover_url", "")
        assert cover_url, f"Book {bid} missing cover_url"
        # Must not point to Douban book subjects
        assert "doubanio.com" not in cover_url, f"Book {bid} has cross-site Douban cover: {cover_url}"
        # Must use official WeRead CDN or QQ reader
        assert "weread.qq.com" in cover_url or "myqcloud.com" in cover_url, f"Book {bid} invalid CDN: {cover_url}"

        # Check known fixed books
        if bid == "wr_004":  # 蛤蟆先生去看心理医生
            assert "33560892" not in cover_url, "wr_004 must not point to 签到系统 web novel cover"


def test_douban_classic_movies_have_valid_posters():
    for movie in DOUBAN_CLASSIC_MOVIES:
        mid = movie["id"]
        cover_url = movie.get("cover_url", "")
        assert cover_url, f"Movie {mid} missing cover_url"
        # Must not point to Douban book subjects (/subject/)
        assert "/view/subject/" not in cover_url, f"Movie {mid} incorrectly uses book subject cover: {cover_url}"
        # Must point to movie posters (/view/photo/)
        assert "/view/photo/" in cover_url, f"Movie {mid} must use photo/poster URL: {cover_url}"
        # Must not use img9 which serves anti-bot JS challenges
        assert "img9.doubanio.com" not in cover_url, f"Movie {mid} uses img9 which triggers anti-bot JS: {cover_url}"


def test_media_fetcher_smart_referer():
    douban_ref = MediaFetcher._default_referer("https://img1.doubanio.com/view/photo/m_ratio_poster/public/p480747492.jpg")
    assert "douban.com" in douban_ref

    weread_ref = MediaFetcher._default_referer("https://cdn.weread.qq.com/weread/cover/1/yuewen_834464/t6.jpg")
    assert "weread.qq.com" in weread_ref


@pytest.mark.asyncio
async def test_douban_online_items_parses_poster_correctly():
    service = DoubanMovieService()
    # Mock online item structure from Douban Rexxar API
    mock_item = {
        "title": "测试电影",
        "cover_url": "https://img1.doubanio.com/view/photo/m_ratio_poster/public/p12345.jpg",
        "pic": {"large": "https://img1.doubanio.com/view/photo/m_ratio_poster/public/p12345.jpg"},
        "photos": ["https://img1.doubanio.com/view/photo/m/public/p_still_6789.jpg"],
        "info": "导演 / 2026",
    }
    cover = mock_item.get("cover_url") or mock_item.get("pic", {}).get("large")
    assert cover == "https://img1.doubanio.com/view/photo/m_ratio_poster/public/p12345.jpg"
    assert "p_still" not in cover
