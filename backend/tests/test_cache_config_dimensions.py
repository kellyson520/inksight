import pytest

from core.cache import ContentCache


def test_cache_key_includes_language_and_config_definition_hash():
    cache = ContentCache()
    base = {"language": "zh", "mode_definition": {"body": [{"type": "text"}]}}
    reordered = {"mode_definition": {"body": [{"type": "text"}]}, "language": "zh"}
    english = {"language": "en", "mode_definition": {"body": [{"type": "text"}]}}
    changed_definition = {"language": "zh", "mode_definition": {"body": [{"type": "big_number"}]}}

    first = cache._get_cache_key("AA:BB", "DAILY", 400, 300, colors=2, config=base)
    same = cache._get_cache_key("AA:BB", "DAILY", 400, 300, colors=2, config=reordered)
    different_language = cache._get_cache_key("AA:BB", "DAILY", 400, 300, colors=2, config=english)
    different_definition = cache._get_cache_key("AA:BB", "DAILY", 400, 300, colors=2, config=changed_definition)

    assert first == same
    assert first != different_language
    assert first != different_definition


def test_cache_key_rejects_unstable_non_json_config():
    cache = ContentCache()
    with pytest.raises(TypeError):
        cache._get_cache_key("AA:BB", "DAILY", config={"bad": object()})
