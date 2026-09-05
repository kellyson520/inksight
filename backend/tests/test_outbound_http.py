from __future__ import annotations

from unittest.mock import Mock, patch

import httpx

from core.outbound_http import OutboundHttp, RequestPolicy


def test_outbound_retries_503_and_returns_attempt_count():
    client = Mock()
    client.get.side_effect = [httpx.Response(503), httpx.Response(200, content=b"ok")]
    http = OutboundHttp(client_factory=lambda **_: client, policy=RequestPolicy(max_attempts=2, backoff_base=0))

    with patch("core.outbound_http.socket.getaddrinfo", return_value=[(2, 1, 6, "", ("93.184.216.34", 443))]):
        response = http.get_bytes("https://example.test/a", policy=RequestPolicy(max_attempts=2, backoff_base=0))

    assert response.content == b"ok"
    assert response.attempts == 2


def test_outbound_rejects_private_url_before_network():
    client = Mock()
    http = OutboundHttp(client_factory=lambda **_: client)

    import pytest
    with pytest.raises(ValueError, match="private"):
        http.get_text("http://127.0.0.1/admin")
    client.get.assert_not_called()


def test_outbound_enforces_response_limit():
    client = Mock()
    client.get.return_value = httpx.Response(200, content=b"12345")
    http = OutboundHttp(client_factory=lambda **_: client)

    import pytest
    with patch("core.outbound_http.socket.getaddrinfo", return_value=[(2, 1, 6, "", ("93.184.216.34", 443))]):
        with pytest.raises(ValueError, match="too large"):
            http.get_bytes("https://example.test/a", policy=RequestPolicy(max_response_bytes=4))
