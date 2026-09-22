"""
测试允许特定服务 (如内部监控探针) 探测内网或本地服务的合规场景：
1. 默认 RequestPolicy(allow_private=False) 拦截私网/本地环回
2. RequestPolicy(allow_private=True) 允许内网探活
"""
import pytest
from core.outbound_http import OutboundHttp, RequestPolicy


def test_default_policy_blocks_private_address():
    with pytest.raises(ValueError) as exc:
        OutboundHttp._validate_url("http://127.0.0.1:8070/api/modes", RequestPolicy())
    assert "private" in str(exc.value).lower() or "blocked" in str(exc.value).lower()


def test_allow_private_policy_permits_internal_probe():
    # 当显式指定 allow_private=True 时，不应抛出私网拦截异常
    policy = RequestPolicy(allow_private=True)
    # 应顺利通过校验
    OutboundHttp._validate_url("http://127.0.0.1:8070/api/modes", policy)
