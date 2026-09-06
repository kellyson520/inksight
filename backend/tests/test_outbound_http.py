from __future__ import annotations

from unittest.mock import Mock, patch

import httpx

from core.outbound_http import OutboundHttp, RequestPolicy
from core.observability import Observability


def test_outbound_retries_503_and_returns_attempt_count():
    client = Mock()
    client.get.side_effect = [httpx.Response(503), httpx.Response(200, content=b"ok")]
    http = OutboundHttp(client_factory=lambda **_: client, policy=RequestPolicy(max_attempts=2, backoff_base=0))

    with patch("core.outbound_http.socket.getaddrinfo", return_value=[(2, 1, 6, "", ("93.184.216.34", 443))]):
        response = http.get_bytes("https://example.test/a", policy=RequestPolicy(max_attempts=2, backoff_base=0))

    assert response.content == b"ok"
    assert response.attempts == 2


def test_outbound_success_is_visible_in_dependency_metrics():
    client = Mock()
    client.get.return_value = httpx.Response(200, content=b"ok")
    http = OutboundHttp(client_factory=lambda **_: client)
    metrics = Observability()
    with patch("core.outbound_http.obs", metrics), patch("core.outbound_http.socket.getaddrinfo", return_value=[(2, 1, 6, "", ("93.184.216.34", 443))]):
        http.get_bytes("https://example.test/a", policy=RequestPolicy(max_attempts=1, backoff_base=0))
    snapshot = metrics.snapshot()["dependency_metrics"]
    assert snapshot["successes"] == 1
    assert snapshot["by_host"]["example.test"]["count"] == 1


def test_outbound_rejects_private_url_before_network():
    client = Mock()
    http = OutboundHttp(client_factory=lambda **_: client)

    import pytest
    with pytest.raises(ValueError, match="private"):
        http.get_text("http://127.0.0.1/admin")
    client.get.assert_not_called()


def test_outbound_stream_enforces_limit_before_consuming_all_chunks():
    client = Mock()

    class StreamResponse:
        status_code = 200
        headers = {}

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def iter_bytes(self):
            yield b"123"
            yield b"45"

    client.stream.return_value = StreamResponse()
    http = OutboundHttp(client_factory=lambda **_: client)

    import pytest
    with patch("core.outbound_http.socket.getaddrinfo", return_value=[(2, 1, 6, "", ("93.184.216.34", 443))]):
        with pytest.raises(ValueError, match="too large"):
            http.get_stream_bytes("https://example.test/a", policy=RequestPolicy(max_response_bytes=4))
    client.stream.assert_called_once()


def test_outbound_stream_returns_complete_content_under_limit():
    client = Mock()

    class StreamResponse:
        status_code = 200
        headers = {"content-type": "image/png"}
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def iter_bytes(self):
            yield b"12"
            yield b"34"

    client.stream.return_value = StreamResponse()
    http = OutboundHttp(client_factory=lambda **_: client)
    with patch("core.outbound_http.socket.getaddrinfo", return_value=[(2, 1, 6, "", ("93.184.216.34", 443))]):
        response = http.get_stream_bytes("https://example.test/a", policy=RequestPolicy(max_response_bytes=4))
    assert response.content == b"1234"
    assert response.headers["content-type"] == "image/png"


def test_outbound_enforces_response_limit():
    client = Mock()
    client.get.return_value = httpx.Response(200, content=b"12345")
    http = OutboundHttp(client_factory=lambda **_: client)

    import pytest
    with patch("core.outbound_http.socket.getaddrinfo", return_value=[(2, 1, 6, "", ("93.184.216.34", 443))]):
        with pytest.raises(ValueError, match="too large"):
            http.get_bytes("https://example.test/a", policy=RequestPolicy(max_response_bytes=4))
