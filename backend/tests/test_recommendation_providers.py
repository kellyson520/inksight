import pytest

from core.providers.qidian_novel_provider import _parse_qidian_items
from core.providers.pixiv_daily_provider import _parse_pixiv_item, _parse_pixiv_items
from core.providers.iwara_video_provider import _parse_iwara_items
from core.providers.porn_video_provider import _parse_porn_items


def test_qidian_parser_normalizes_ranked_novels():
    items = _parse_qidian_items({"data": [{"bookName": "诡秘之主", "authorName": "爱潜水的乌贼", "rank": 1}]})
    assert items[0]["title"] == "诡秘之主"
    assert items[0]["subtitle"] == "爱潜水的乌贼"
    assert items[0]["rank_label"] == "NO.1"


def test_pixiv_provider_uses_public_endpoint_and_proxy():
    import asyncio
    from unittest.mock import patch
    from core.providers.pixiv_daily_provider import generate_pixiv_daily

    response = type("Response", (), {"json": lambda self: {"title": "Blue", "author": "Artist", "urls": {"regular": "https://i.pximg.net/r.jpg", "original": "https://i.pximg.net/o.jpg"}, "pid": 123}})()
    with patch("core.providers.pixiv_daily_provider.outbound_http.get_json", return_value=response) as get_json:
        result = asyncio.run(generate_pixiv_daily({}, {}, {}, config={"global_proxy_url": "http://proxy.example:8080"}))
    assert result["items"][0]["cover_url"].endswith("o.jpg")
    assert get_json.call_args.args[0].startswith("https://")
    assert get_json.call_args.kwargs["proxy_url"] == "http://proxy.example:8080"
    assert get_json.call_args.kwargs["headers"]["Referer"] == "https://www.pixiv.net/"


def test_pixiv_fallback_contains_renderable_public_image():
    import asyncio
    from core.providers.pixiv_daily_provider import generate_pixiv_daily
    result = asyncio.run(generate_pixiv_daily({}, {"type": "computed"}, {"title": "Pixiv 每日一图"}, config={}))
    assert result["items"]
    assert result["items"][0].get("image_data") is not None


def test_pixiv_parser_normalizes_daily_image():
    item = _parse_pixiv_item({"title": "Blue", "user": {"name": "Artist"}, "image": "https://i.pximg.net/a.jpg"})
    assert item["title"] == "Blue"
    assert item["subtitle"] == "Artist"
    assert item["cover_url"].startswith("https://")


def test_pixiv_parser_supports_public_data_urls_shape():
    item = _parse_pixiv_item({
        "title": "Blue",
        "author": "Artist",
        "urls": {"regular": "https://i.pximg.net/img-regular.jpg", "original": "https://i.pximg.net/img-original.jpg"},
        "pid": 123,
    })
    assert item["thumbnail_url"] == "https://i.pximg.net/img-regular.jpg"
    assert item["cover_url"] == "https://i.pximg.net/img-original.jpg"
    assert item["detail_url"].endswith("/artworks/123")


def test_pixiv_parser_supports_lolicon_pixiv_data_list():
    from core.providers.pixiv_daily_provider import _parse_pixiv_items
    items = _parse_pixiv_items({"data": [{
        "pid": 789,
        "title": "Mirror Blue",
        "author": "Artist",
        "urls": {"regular": "https://i.pixiv.re/regular.jpg", "original": "https://i.pixiv.re/original.jpg"},
    }]})
    assert items[0]["thumbnail_url"].endswith("regular.jpg")
    assert items[0]["cover_url"].endswith("original.jpg")
    assert items[0]["detail_url"].endswith("/artworks/789")


def test_pixiv_parser_supports_ajax_body_illust_list():
    items = _parse_pixiv_items({
        "error": False,
        "body": {"illust": [{
            "id": 456,
            "title": "Daily Blue",
            "userName": "Artist",
            "urls": {"regular": "https://i.pximg.net/regular.jpg", "original": "https://i.pximg.net/original.jpg"},
        }]},
    })
    assert items[0]["title"] == "Daily Blue"
    assert items[0]["thumbnail_url"].endswith("regular.jpg")
    assert items[0]["cover_url"].endswith("original.jpg")


def test_iwara_parser_normalizes_video_list():
    items = _parse_iwara_items({"results": [{"title": "MMD", "user": {"username": "alice"}, "thumbnail": "https://img.example/a.jpg"}]})
    assert items[0]["title"] == "MMD"
    assert items[0]["subtitle"] == "alice"


def test_porn_parser_normalizes_video_list_without_sensitive_fields():
    items = _parse_porn_items([{"title": "Public video", "thumbnail": "https://img.example/v.jpg", "url": "https://www.pornhub.com/view_video.php?viewkey=abc"}])
    assert items[0]["title"] == "Public video"
    assert items[0]["detail_url"].startswith("https://")
