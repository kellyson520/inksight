from __future__ import annotations

from unittest.mock import Mock

import httpx

from core.media_fetcher import MediaFetchResult, MediaFetcher


def test_render_image_uses_shared_fetcher(monkeypatch):
    from core.blocks import components

    assert "httpx.Client" not in components.render_image.__code__.co_names
    monkeypatch.setattr(
        components.media_fetcher,
        "fetch",
        lambda urls: MediaFetchResult(data=b"not-used", url=str(urls), cache_hit=False),
    )
    assert hasattr(components, "media_fetcher")


def test_image_block_passes_url_candidates(monkeypatch):
    from PIL import Image
    from core.blocks import components
    from core.blocks.context import RenderContext

    captured = {}
    class FakeFetcher:
        def fetch_image(self, urls):
            captured["urls"] = urls
            out = Image.new("RGB", (4, 4), "white")
            import io
            buf = io.BytesIO()
            out.save(buf, format="PNG")
            return MediaFetchResult(data=buf.getvalue(), url=str(urls[-1]), cache_hit=False)

    monkeypatch.setattr(components, "media_fetcher", FakeFetcher())
    img = Image.new("1", (80, 80), 1)
    ctx = RenderContext(draw=__import__("PIL").ImageDraw.Draw(img), img=img, content={
        "cover_url": "https://bad.test/a",
        "cover_urls": ["https://bad.test/a", "https://good.test/a"],
    }, screen_w=80, screen_h=80, y=0, footer_height=0)
    components.render_image(ctx, {"field": "cover_url", "urls_field": "cover_urls", "width": 4, "height": 4})

    assert captured["urls"] == ["https://bad.test/a", "https://good.test/a"]


def test_fetch_retries_transient_timeout_then_succeeds(tmp_path):
    responses = [httpx.ReadTimeout("slow"), httpx.Response(503), httpx.Response(200, content=b"ok")]
    client = Mock()
    client.get.side_effect = responses
    fetcher = MediaFetcher(cache_dir=tmp_path, client_factory=lambda **_: client, backoff_base=0)

    result = fetcher.fetch("https://cdn.example.test/a.jpg")

    assert result.data == b"ok"
    assert result.cache_hit is False
    assert client.get.call_count == 3


def test_fetch_switches_permanently_failed_url_to_candidate(tmp_path):
    client = Mock()
    client.get.side_effect = [httpx.Response(404), httpx.Response(200, content=b"fallback")]
    fetcher = MediaFetcher(cache_dir=tmp_path, client_factory=lambda **_: client, backoff_base=0)

    result = fetcher.fetch(["https://bad.example.test/a.jpg", "https://good.example.test/a.jpg"])

    assert result.url == "https://good.example.test/a.jpg"
    assert result.data == b"fallback"
    assert client.get.call_count == 2


def test_fetch_uses_disk_cache_without_network(tmp_path):
    client = Mock()
    client.get.return_value = httpx.Response(200, content=b"cached")
    fetcher = MediaFetcher(cache_dir=tmp_path, client_factory=lambda **_: client, backoff_base=0)
    first = fetcher.fetch("https://cdn.example.test/a.jpg")
    client.get.reset_mock()
    second_fetcher = MediaFetcher(cache_dir=tmp_path, client_factory=lambda **_: client, backoff_base=0)

    second = second_fetcher.fetch("https://cdn.example.test/a.jpg")

    assert first.data == second.data == b"cached"
    assert second.cache_hit is True
    client.get.assert_not_called()


def test_fetch_sends_domain_referer(tmp_path):
    client = Mock()
    client.get.return_value = httpx.Response(200, content=b"ok")
    fetcher = MediaFetcher(cache_dir=tmp_path, client_factory=lambda **_: client, backoff_base=0)

    fetcher.fetch("https://img.example.test/a.jpg")

    headers = client.get.call_args.kwargs["headers"]
    assert headers["Referer"] == "https://img.example.test/"
    assert "User-Agent" in headers


def test_failed_url_enters_cooldown_and_skips_duplicate_request(tmp_path):
    client = Mock()
    client.get.return_value = httpx.Response(404)
    fetcher = MediaFetcher(
        cache_dir=tmp_path,
        client_factory=lambda **_: client,
        max_attempts=1,
        backoff_base=0,
        failure_cooldown=60,
    )

    import pytest
    with pytest.raises(Exception):
        fetcher.fetch("https://bad.example.test/a.jpg")
    with pytest.raises(Exception) as second:
        fetcher.fetch("https://bad.example.test/a.jpg")

    assert client.get.call_count == 1
    assert "cooldown" in str(second.value)


def test_corrupt_or_empty_cache_file_is_removed(tmp_path):
    fetcher = MediaFetcher(cache_dir=tmp_path, client_factory=lambda **_: Mock(), backoff_base=0)
    url = "https://cdn.example.test/corrupt.jpg"
    cache_path = fetcher._cache_path(url)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_bytes(b"")

    assert fetcher._read_cache(url) is None
    assert not cache_path.exists()


def test_invalid_numeric_environment_values_use_safe_defaults(monkeypatch, tmp_path):
    monkeypatch.setenv("INKSIGHT_MEDIA_MAX_ATTEMPTS", "nan")
    monkeypatch.setenv("INKSIGHT_MEDIA_TIMEOUT_READ", "inf")
    fetcher = MediaFetcher(cache_dir=tmp_path, client_factory=lambda **_: Mock(), backoff_base=0)

    assert fetcher.max_attempts == 3
    assert fetcher.timeout.read == 10.0


def test_fetch_rejects_oversized_response(tmp_path):
    client = Mock()
    client.get.return_value = httpx.Response(200, content=b"1" * 2048)
    fetcher = MediaFetcher(cache_dir=tmp_path, client_factory=lambda **_: client, max_attempts=1, max_response_bytes=1024, backoff_base=0)

    import pytest
    with pytest.raises(Exception) as exc:
        fetcher.fetch("https://cdn.example.test/large.jpg")
    assert "response too large" in str(exc.value)


def test_fetch_rejects_local_and_non_http_urls(tmp_path):
    client = Mock()
    fetcher = MediaFetcher(cache_dir=tmp_path, client_factory=lambda **_: client, backoff_base=0)

    import pytest
    for url in ["file:///etc/passwd", "http://127.0.0.1/admin", "http://localhost/admin"]:
        with pytest.raises(Exception):
            fetcher.fetch(url)
    client.get.assert_not_called()


def test_fetch_does_not_follow_redirects_into_private_network(tmp_path):
    client = Mock()
    client.get.return_value = httpx.Response(302, headers={"location": "http://127.0.0.1/admin"})
    fetcher = MediaFetcher(cache_dir=tmp_path, client_factory=lambda **_: client, max_attempts=1, backoff_base=0)

    import pytest
    with pytest.raises(Exception):
        fetcher.fetch("https://cdn.example.test/a.jpg")
    assert client.get.call_args.kwargs.get("follow_redirects") is False


def test_fetch_image_skips_html_success_and_uses_next_candidate(tmp_path):
    from io import BytesIO
    from PIL import Image
    valid = BytesIO()
    Image.new("RGB", (2, 2), "white").save(valid, format="PNG")
    client = Mock()
    client.get.side_effect = [
        httpx.Response(200, headers={"content-type": "text/html"}, content=b"<html>blocked</html>"),
        httpx.Response(200, headers={"content-type": "image/png"}, content=valid.getvalue()),
    ]
    fetcher = MediaFetcher(cache_dir=tmp_path, client_factory=lambda **_: client, max_attempts=1, backoff_base=0)

    result = fetcher.fetch_image(["https://bad.example.test/a.jpg", "https://good.example.test/a.jpg"])

    assert result.url == "https://good.example.test/a.jpg"
    assert result.data == valid.getvalue()
    assert client.get.call_count == 2
