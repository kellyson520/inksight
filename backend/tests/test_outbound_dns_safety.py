from unittest.mock import patch

import pytest

from core.outbound_http import OutboundHttp


def test_validate_url_rejects_hostname_resolving_to_private_ip():
    policy = OutboundHttp().policy
    with patch("core.outbound_http.socket.getaddrinfo", return_value=[
        (2, 1, 6, "", ("127.0.0.1", 443)),
    ]):
        with pytest.raises(ValueError, match="private URL blocked"):
            OutboundHttp._validate_url("https://public.example/data", policy)


def test_validate_url_allows_hostname_resolving_to_public_ip():
    policy = OutboundHttp().policy
    with patch("core.outbound_http.socket.getaddrinfo", return_value=[
        (2, 1, 6, "", ("93.184.216.34", 443)),
    ]):
        OutboundHttp._validate_url("https://public.example/data", policy)
