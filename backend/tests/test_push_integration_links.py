"""
监控与灾害报警自动联动推送测试 (Monitor & Disaster Push Integration Tests)
"""
from __future__ import annotations

import pytest
import asyncio
from core.monitor_service import monitor_service
from core.push_service import push_dispatcher
from httpx import AsyncClient, ASGITransport
from api.index import app
from core.auth import create_session_token


@pytest.mark.asyncio
async def test_monitor_change_triggers_push():
    """验证当 MonitorService 产生内容变更通知时，自动派发设备告警。"""
    mac = "70:AF:09:75:51:84"
    notice = monitor_service.create_change_notice(
        target_id="tgt_test",
        site_name="Test Production Site",
        url="https://example.com",
        title="Site Content Modified",
        prev_snippet="Old Text",
        new_snippet="New Text Updated",
        target_mac=mac,
    )
    assert notice["target_mac"] == mac

    # 异步调度微任务推进
    await asyncio.sleep(0.1)

    logs = push_dispatcher.get_recent_logs()
    device_logs = [l for l in logs if l["target"] == mac and l["channel"] == "device"]
    assert len(device_logs) > 0
    assert "MONITOR" in device_logs[0]["summary"]


@pytest.mark.asyncio
async def test_disaster_alert_push_triggers_multi_channel():
    """验证灾害预警主动下发时联动推送。"""
    from core.config_store import upsert_device_membership, create_user
    transport = ASGITransport(app=app)
    mac = "70:AF:09:75:51:84"
    
    # 确保用户存在并赋予 Owner 权限
    try:
        await create_user(username="testuser", password_hash="hash")
    except Exception:
        pass
    await upsert_device_membership(mac=mac, user_id=1, role="owner", status="active")

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = create_session_token(user_id=1, username="testuser")
        cookies = {"ink_session": token}

        payload = {
            "headline": "台风红色预警",
            "level": "red",
            "description": "超强台风逼近，请做好防御准备",
        }
        resp = await client.post(
            f"/api/device/{mac}/disaster-alert/push",
            json=payload,
            cookies=cookies,
        )
        assert resp.status_code == 200

        logs = push_dispatcher.get_recent_logs()
        disaster_logs = [l for l in logs if l["target"] == mac and "DISASTER_ALERT" in l["summary"]]
        assert len(disaster_logs) > 0
