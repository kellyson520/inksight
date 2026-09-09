import pytest

from core.config_store import _default_user_preferences
from core.recommendation_provider import resolve_proxy_url


def test_default_preferences_include_empty_global_proxy():
    assert _default_user_preferences(7)["global_proxy_url"] == ""


def test_proxy_preference_accepts_supported_schemes_only():
    assert resolve_proxy_url("https://proxy.example:8443")
    assert resolve_proxy_url("socks5://proxy.example:1080")
    assert resolve_proxy_url("ftp://proxy.example:21") is None
