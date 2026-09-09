import pytest

from core.providers.qidian_novel_provider import _parse_qidian_items
from core.providers.pixiv_daily_provider import _parse_pixiv_item
from core.providers.iwara_video_provider import _parse_iwara_items
from core.providers.porn_video_provider import _parse_porn_items


def test_qidian_parser_normalizes_ranked_novels():
    items = _parse_qidian_items({"data": [{"bookName": "诡秘之主", "authorName": "爱潜水的乌贼", "rank": 1}]})
    assert items[0]["title"] == "诡秘之主"
    assert items[0]["subtitle"] == "爱潜水的乌贼"
    assert items[0]["rank_label"] == "NO.1"


def test_pixiv_parser_normalizes_daily_image():
    item = _parse_pixiv_item({"title": "Blue", "user": {"name": "Artist"}, "image": "https://i.pximg.net/a.jpg"})
    assert item["title"] == "Blue"
    assert item["subtitle"] == "Artist"
    assert item["cover_url"].startswith("https://")


def test_iwara_parser_normalizes_video_list():
    items = _parse_iwara_items({"results": [{"title": "MMD", "user": {"username": "alice"}, "thumbnail": "https://img.example/a.jpg"}]})
    assert items[0]["title"] == "MMD"
    assert items[0]["subtitle"] == "alice"


def test_porn_parser_normalizes_video_list_without_sensitive_fields():
    items = _parse_porn_items([{"title": "Public video", "thumbnail": "https://img.example/v.jpg", "url": "https://www.pornhub.com/view_video.php?viewkey=abc"}])
    assert items[0]["title"] == "Public video"
    assert items[0]["detail_url"].startswith("https://")
