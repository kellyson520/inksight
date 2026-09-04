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
