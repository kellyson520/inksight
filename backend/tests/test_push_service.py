"""
InkSight 多渠道推送服务与底层自愈机制测试 (Push Service & Healing Tests)
"""
from __future__ import annotations

import pytest
from core.push_service import push_dispatcher


@pytest.mark.asyncio
async def test_push_to_device_in_memory_queue():
    """验证向设备队列推送告警成功入队。"""
    mac = "AA:BB:CC:11:22:33"
    ok = await push_dispatcher.push_to_device(
        mac=mac,
        sender="TEST_SENDER",
        message="Emergency test alert message",
        level="critical",
    )
    assert ok is True
    logs = push_dispatcher.get_recent_logs()
    assert len(logs) > 0
    assert logs[0]["channel"] == "device"
    assert logs[0]["target"] == mac
    assert logs[0]["success"] is True


@pytest.mark.asyncio
async def test_broadcast_alert_to_multiple_devices():
    """验证多设备广播调度。"""
    macs = ["11:22:33:44:55:66", "22:33:44:55:66:77"]
    res = await push_dispatcher.broadcast_alert(
        title="Broadcast Title",
        message="System Maintenance Notice",
        level="warning",
        target_macs=macs,
    )
    assert res["total"] == 2
    assert res["success"] == 2
    assert res["failed"] == 0


@pytest.mark.asyncio
async def test_push_to_bark_graceful_handling():
    """验证无效 Key 时 Bark 返回 False 并平稳记录，不引发系统未捕获崩溃。"""
    ok = await push_dispatcher.push_to_bark(
        bark_key="invalid_test_key_xyz",
        title="Test Bark",
        body="Body Content",
    )
    assert ok is False
    logs = push_dispatcher.get_recent_logs()
    assert any(log["channel"] == "bark" for log in logs)


@pytest.mark.asyncio
async def test_push_to_wechat_webhook_graceful_handling():
    """验证无效 Webhook URL 时的平稳处理。"""
    ok = await push_dispatcher.push_to_wechat_webhook(
        webhook_url="https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=invalid_demo_key",
        title="WeChat Alert",
        content="Test content",
    )
    assert ok is False
