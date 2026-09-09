from unittest.mock import Mock

import httpx

from core.outbound_http import OutboundHttp, RequestPolicy


def test_outbound_http_passes_proxy_to_client_factory():
    factory = Mock()
    client = Mock()
    client.__enter__ = Mock(return_value=client)
    client.__exit__ = Mock(return_value=None)
    client.get.return_value = httpx.Response(200, content=b'{"ok":true}')
    factory.return_value = client

    http = OutboundHttp(client_factory=factory)
    response = http.get_json(
        "https://example.com/data.json",
        proxy_url="http://proxy.example:8080",
        policy=RequestPolicy(max_attempts=1),
    )

    assert response.json() == {"ok": True}
    assert factory.call_args.kwargs["proxy"] == "http://proxy.example:8080"


def test_media_fetcher_passes_configured_proxy_to_outbound_http():
    from unittest.mock import patch
    from core.media_fetcher import MediaFetcher

    fetcher = MediaFetcher(backoff_base=0, failure_cooldown=0)
    with patch("core.media_fetcher.outbound_http.get_stream_bytes") as get_stream:
        get_stream.return_value = httpx.Response(200, content=b"not-an-image")
        fetcher._get("https://img.example/a.jpg", {}, proxy_url="http://proxy.example:8080")
    assert get_stream.call_args.kwargs["proxy_url"] == "http://proxy.example:8080"
