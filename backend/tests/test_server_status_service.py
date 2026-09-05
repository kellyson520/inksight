"""
Unit tests for ServerStatusService and endpoints.
"""
from core.server_status_service import ServerStatusService


def test_server_status_local_metrics():
    svc = ServerStatusService()
    metrics = svc.get_local_metrics()
    assert "cpu_pct" in metrics
    assert "mem_pct" in metrics
    assert "disk_pct" in metrics
    assert "load_str" in metrics
    assert "uptime" in metrics
    assert metrics["source"] == "local"


def test_server_status_pushed_metrics_lifecycle():
    svc = ServerStatusService()
    record = svc.record_pushed_metrics(
        "test-node",
        {
            "server_name": "Node-Test-01",
            "cpu_pct": 55.4,
            "mem_pct": 62.1,
            "disk_pct": 45.0,
            "uptime": "20天",
        },
    )
    assert record["server_name"] == "Node-Test-01"
    assert record["cpu_pct"] == 55.4
    assert record["source"] == "pushed"

    fetched = svc.get_metrics_for_mode("test-node")
    assert fetched["server_name"] == "Node-Test-01"
    assert fetched["cpu_pct"] == 55.4


def test_server_status_script_generation():
    svc = ServerStatusService()
    script = svc.generate_shell_script("https://example.com/api/server-status", "VPS-Prod")
    assert "https://example.com/api/server-status" in script
    assert "VPS-Prod" in script
    assert "cpu_sample()" in script
    assert "mem_info()" in script
    assert "curl -s -X POST" in script


def test_server_status_persistent_rename():
    svc = ServerStatusService()
    # 1. 设定持久化名称
    res = svc.set_server_name("default", "家庭生产NAS")
    assert res == "家庭生产NAS"
    assert svc.get_server_name("default") == "家庭生产NAS"

    # 2. 本地指标中正确应用该名称
    metrics = svc.get_local_metrics()
    assert metrics["server_name"] == "家庭生产NAS"

    # 3. 跨实例持久化恢复测试
    new_svc = ServerStatusService()
    assert new_svc.get_server_name("default") == "家庭生产NAS"
    assert new_svc.get_local_metrics()["server_name"] == "家庭生产NAS"

    # 4. 指定 key 节点的重命名
    svc.set_server_name("vps-sgp", "新加坡云服-01")
    assert svc.get_server_name("vps-sgp") == "新加坡云服-01"
    fetched = svc.get_metrics_for_mode("vps-sgp")
    assert fetched["server_name"] == "新加坡云服-01"
