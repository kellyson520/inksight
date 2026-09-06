from unittest.mock import Mock, patch

import httpx
import pytest

from core.outbound_http import OutboundHttp, RequestPolicy


def _client_factory(responses):
    client = Mock()
    client.get.side_effect = responses
    return client


def test_follow_redirects_rejects_private_redirect_target():
    client = _client_factory([
        httpx.Response(302, headers={"location": "http://127.0.0.1/admin"}),
    ])
    http = OutboundHttp(client_factory=lambda **_: client)
    with patch("core.outbound_http.socket.getaddrinfo", return_value=[(2, 1, 6, "", ("93.184.216.34", 443))]):
        with pytest.raises(ValueError, match="private URL blocked"):
            http.get_bytes("https://public.example/start", policy=RequestPolicy(follow_redirects=True, backoff_base=0))
    assert client.get.call_count == 1


def test_follow_redirects_revalidates_each_public_target():
    client = _client_factory([
        httpx.Response(302, headers={"location": "https://next.example/page"}),
        httpx.Response(200, content=b"ok"),
    ])
    http = OutboundHttp(client_factory=lambda **_: client)
    with patch("core.outbound_http.socket.getaddrinfo", side_effect=[
        [(2, 1, 6, "", ("93.184.216.34", 443))],
        [(2, 1, 6, "", ("93.184.216.35", 443))],
    ]):
        response = http.get_bytes("https://public.example/start", policy=RequestPolicy(follow_redirects=True, backoff_base=0))
    assert response.content == b"ok"
    assert response.url == "https://next.example/page"
    assert client.get.call_count == 2


def test_validate_url_rejects_carrier_grade_nat_address():
    policy = RequestPolicy()
    with pytest.raises(ValueError, match="private URL blocked"):
        OutboundHttp._validate_url("http://100.64.0.1/status", policy)
