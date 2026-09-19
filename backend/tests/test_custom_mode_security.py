"""
测试自定义模式 (Custom Modes) 安全加固：
1. 阻止任何包含路径穿越字符 (../, \\, 斜杠, 特殊字符) 的 mode_id
2. 限制 mode_id 必须为字母、数字和下划线
"""
import pytest
from core.mode_registry import _validate_mode_def_with_error


def test_validate_mode_def_rejects_path_traversal_mode_id():
    malicious_mode_ids = [
        "../../etc/passwd",
        "../custom_test",
        "evil/mode",
        "mode\x00null",
        "mode;rm -rf",
        "..\\..\\win.ini",
        "a" * 65,  # 超过 64 字符
        "",
    ]

    base_def = {
        "content": {
            "type": "llm",
            "prompt_template": "Test prompt",
            "fallback": {"text": "fallback"},
        },
        "layout": {
            "body": [{"type": "text", "field": "text"}]
        }
    }

    for mid in malicious_mode_ids:
        d = dict(base_def, mode_id=mid)
        ok, err = _validate_mode_def_with_error(d)
        assert not ok, f"mode_id '{mid}' should be rejected"
        assert err is not None


def test_validate_mode_def_allows_valid_mode_id():
    base_def = {
        "mode_id": "MY_CUSTOM_MODE_1",
        "content": {
            "type": "llm",
            "prompt_template": "Test prompt",
            "fallback": {"text": "fallback"},
        },
        "layout": {
            "body": [{"type": "text", "field": "text"}]
        }
    }
    ok, err = _validate_mode_def_with_error(base_def)
    assert ok, f"valid mode_id failed: {err}"
