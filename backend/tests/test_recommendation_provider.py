from core.recommendation_provider import normalize_recommendation_item, resolve_proxy_url


def test_normalize_recommendation_item_fills_safe_defaults():
    item = normalize_recommendation_item({"title": "  Novel  ", "cover": "https://img.example/a.jpg"}, source="Qidian")
    assert item["title"] == "Novel"
    assert item["cover_url"] == "https://img.example/a.jpg"
    assert item["source"] == "Qidian"
    assert item["rank_label"] == "推荐"


def test_resolve_proxy_url_accepts_http_and_socks_schemes():
    assert resolve_proxy_url(" http://proxy.example:8080 ") == "http://proxy.example:8080"
    assert resolve_proxy_url("socks5h://proxy.example:1080") == "socks5h://proxy.example:1080"


def test_resolve_proxy_url_rejects_unsafe_scheme_and_credentials_are_redacted():
    assert resolve_proxy_url("ftp://proxy.example/file") is None
    value = resolve_proxy_url("http://user:secret@proxy.example:8080")
    assert value == "http://user:secret@proxy.example:8080"
