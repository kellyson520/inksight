"""
测试核心 OutboundHttp 的 SSRF 防护加固：
1. 多 IP / DNS Round-Robin 包含私网 IP 时必须严格拦截 (不能被 any/all 绕过)
2. IPv6-mapped IPv4 (如 ::ffff:127.0.0.1, ::ffff:169.254.169.254) 必须严格拦截
"""
from unittest.mock import patch
import pytest

from core.outbound_http import OutboundHttp, RequestPolicy


def test_rejects_multi_ip_containing_private_address():
    """测试当域名解析出多个 IP，只要其中包含私有/环回/保留 IP，即坚决拦截。"""
    policy = OutboundHttp().policy
    # 模拟攻击者通过同时解析公网 IP 与本地环回 IP 企图绕过 all() 检查
    with patch("core.outbound_http.socket.getaddrinfo", return_value=[
        (2, 1, 6, "", ("93.184.216.34", 443)),
        (2, 1, 6, "", ("127.0.0.1", 443)),
    ]):
        with pytest.raises(ValueError, match="private URL blocked"):
            OutboundHttp._validate_url("https://dual-homed-attack.example/data", policy)


def test_rejects_ipv6_mapped_ipv4_private_addresses():
    """测试 IPv6-mapped IPv4 格式地址无论作为直接 IP 还是 DNS 解析结果均被拦截。"""
    policy = OutboundHttp().policy

    # 1. 直接 IPv6-mapped 环回地址 [::ffff:127.0.0.1]
    with pytest.raises(ValueError, match="private URL blocked"):
        OutboundHttp._validate_url("http://[::ffff:127.0.0.1]/status", policy)

    # 2. 云厂商元数据地址 [::ffff:169.254.169.254]
    with pytest.raises(ValueError, match="private URL blocked"):
        OutboundHttp._validate_url("http://[::ffff:169.254.169.254]/latest/meta-data", policy)

    # 3. 私网地址 [::ffff:192.168.1.1]
    with pytest.raises(ValueError, match="private URL blocked"):
        OutboundHttp._validate_url("http://[::ffff:192.168.1.1]/admin", policy)
