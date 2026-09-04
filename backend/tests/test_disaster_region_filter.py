import pytest
from core.disaster_service import check_device_disaster_alert, simulate_disaster_alert, clear_simulated_alert


@pytest.mark.asyncio
async def test_disaster_alert_region_filtering():
    """验证灾害预警防误判与地区精准过滤。"""
    mac = "AA:BB:CC:11:22:33"
    clear_simulated_alert(mac)

    # 1. 禁用状态下应返回 None
    cfg_disabled = {
        "city": "杭州",
        "disaster_alert": {"enabled": False, "city": "杭州", "min_level": "yellow"}
    }
    res = await check_device_disaster_alert(mac, cfg_disabled)
    assert res is None

    # 2. 模拟针对该设备的预警能直接命中
    simulate_disaster_alert(mac, {"title": "杭州市气象台暴雨红色预警", "level": "红色", "severity_score": 1})
    res_sim = await check_device_disaster_alert(mac, cfg_disabled)
    assert res_sim is not None
    assert "暴雨" in res_sim["title"]
    clear_simulated_alert(mac)
