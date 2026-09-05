from unittest.mock import Mock
import httpx
import pytest
from core.outbound_http import OutboundHttp, RequestPolicy


def test_non_retryable_404_is_requested_once():
    client = Mock()
    client.get.return_value = httpx.Response(404)
    http = OutboundHttp(client_factory=lambda **_: client)
    with pytest.raises(ValueError, match="HTTP 404"):
        http.get_bytes("https://example.test/missing")
    assert client.get.call_count == 1


def test_outbound_supports_single_attempt_json_post():
    client = Mock()
    client.post.return_value = httpx.Response(200, json={"ok": True})
    http = OutboundHttp(client_factory=lambda **_: client)

    response = http.post_json("https://example.test/rank", json_body={"page": 1})

    assert response.json() == {"ok": True}
    client.post.assert_called_once()


def test_redirects_are_not_followed_by_default():
    client = Mock()
    client.get.return_value = httpx.Response(302, headers={"location": "https://example.test/next"})
    http = OutboundHttp(client_factory=lambda **_: client)
    with pytest.raises(ValueError, match="HTTP 302"):
        http.get_bytes("https://example.test/start", policy=RequestPolicy(max_attempts=1))
    assert client.get.call_args.kwargs["follow_redirects"] is False
