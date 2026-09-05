from core.cache import ContentCache


def test_content_cache_key_separates_color_dimensions():
    cache = ContentCache()
    assert cache._get_cache_key("AA", "DAILY", 400, 300, colors=2) != cache._get_cache_key("AA", "DAILY", 400, 300, colors=3)
