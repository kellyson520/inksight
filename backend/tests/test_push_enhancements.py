"""
测试完善后的消息与设备告警推送机制（持久化队列、Peek+ACK 确认投递、多渠道分发与统计）
"""
import pytest
from datetime import datetime, timedelta
from core.device_alert_store import DeviceAlertQueue
from core.push_service import push_dispatcher
from core.db import close_all


@pytest.fixture(autouse=True)
async def cleanup_db():
    yield
    await close_all()


@pytest.mark.asyncio
async def test_device_alert_queue_peek_and_ack_flow(tmp_path):
    """测试设备告警队列的 Peek 窥视与 ACK 确认机制，保障弱网环境下消息不丢失。"""
    db_path = tmp_path / "test_alerts.sqlite"
    queue = DeviceAlertQueue(db_path, per_device_limit=5)
    mac = "AA:BB:CC:11:22:33"

    # 1. 初始状态为空
    stats = await queue.get_queue_stats(mac)
    assert stats["pending_count"] == 0

    # 2. 入队一条带过期时间的消息
    alert = {
        "sender": "TEST_BOT",
        "message": "系统告警：服务器 CPU 使用率 > 90%",
        "level": "warning",
        "expires_at": (datetime.now() + timedelta(minutes=5)).isoformat(),
    }
    await queue.enqueue(mac, alert)

    # 3. 统计待办数变为 1
    stats = await queue.get_queue_stats(mac)
    assert stats["pending_count"] == 1

    # 4. 执行 peek：获取消息但队列不出队，状态保留
    peeked = await queue.peek(mac)
    assert peeked is not None
    assert peeked["sender"] == "TEST_BOT"
    assert peeked["message"] == "系统告警：服务器 CPU 使用率 > 90%"
    assert "alert_id" in peeked
    alert_id = peeked["alert_id"]

    # 再次 peek 依然能拿到同一条，pending_count 保持为 1
    peeked_again = await queue.peek(mac)
    assert peeked_again["alert_id"] == alert_id
    stats = await queue.get_queue_stats(mac)
    assert stats["pending_count"] == 1

    # 5. 执行 ack：客户端确认成功处理，消息正式出队删除
    ack_res = await queue.ack(alert_id)
    assert ack_res is True

    # 6. 再次 peek 返回空，pending_count 归零
    peeked_after = await queue.peek(mac)
    assert peeked_after is None
    stats = await queue.get_queue_stats(mac)
    assert stats["pending_count"] == 0


@pytest.mark.asyncio
async def test_device_alert_queue_auto_drops_expired_on_peek(tmp_path):
    """测试当消息已过期时，peek 自动跳过并忽略过期消息。"""
    db_path = tmp_path / "test_expired.sqlite"
    queue = DeviceAlertQueue(db_path, per_device_limit=5)
    mac = "11:22:33:44:55:66"

    # 入队一条过去时间戳的消息（已过期）
    alert_expired = {
        "sender": "OLD_MSG",
        "message": "这是一条过期的紧急通知",
        "level": "info",
        "expires_at": (datetime.now() - timedelta(minutes=1)).isoformat(),
    }
    await queue.enqueue(mac, alert_expired)

    # peek 返回 None
    assert await queue.peek(mac) is None


@pytest.mark.asyncio
async def test_push_dispatcher_broadcast_stats_and_logging():
    """测试 PushDispatcher 广播统计与日志记录能力。"""
    macs = ["AA:BB:CC:00:11:01", "AA:BB:CC:00:11:02"]
    res = await push_dispatcher.broadcast_alert(
        title="天气预警",
        message="暴雨橙色预警，请关好门窗",
        level="warning",
        target_macs=macs,
    )
    assert res["total"] == 2
    assert res["success"] == 2
    assert res["failed"] == 0

    logs = push_dispatcher.get_recent_logs()
    assert len(logs) >= 2
    assert any("暴雨橙色预警" in log["summary"] for log in logs)


@pytest.mark.asyncio
async def test_dispatch_scheduled_user_pushes_dedup_and_resilience(monkeypatch):
    """测试每日定时推送：时间触发、多平台分发、内容不重复与当日防重机制。"""
    import time
    from unittest.mock import AsyncMock, patch
    from core.config_store import save_user_preferences, register_push_token, create_user

    ts = int(time.time() * 1000)
    uid = await create_user(f"push_user_{ts}", "password123", email=f"push_user_{ts}@example.com")
    assert uid is not None

    # 保存推送偏好
    await save_user_preferences(uid, {
        "push_enabled": True,
        "push_time": "08:00",
        "push_modes": ["DAILY", "QUESTION"],
    })

    # 注册 Bark 推送凭据
    await register_push_token(uid, "test_bark_device_key", "bark", "Asia/Shanghai", push_time="08:00")

    # Mock 外部 HTTP 推送
    with patch.object(push_dispatcher, "push_to_bark", new_callable=AsyncMock, return_value=True) as mock_bark:
        import datetime, zoneinfo
        test_now = datetime.datetime(2026, 9, 24, 8, 0, tzinfo=zoneinfo.ZoneInfo("Asia/Shanghai"))

        # 1. 触发定时推送
        res = await push_dispatcher.dispatch_scheduled_user_pushes(test_user_now=test_now)
        assert res["total"] >= 1
        assert res["dispatched"] >= 1
        assert mock_bark.called

        # 验证推送正文
        call_args = mock_bark.call_args[0]
        title, body = call_args[1], call_args[2]
        assert "InkSight" in title
        assert len(body) > 10

        # 2. 同一天再次触发，当日防重拦截
        mock_bark.reset_mock()
        res_repeat = await push_dispatcher.dispatch_scheduled_user_pushes(test_user_now=test_now)
        assert res_repeat["dispatched"] == 0
        assert not mock_bark.called
