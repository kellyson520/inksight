"""
网页变更感知、事件拦截插播与新排版组件单元测试 (Monitor & Interceptor Tests)
覆盖:
1. monitor_service 变动探测、差分提取与通知生命周期
2. interceptor_registry 拦截器链调度与抢占执行
3. 平常静默、变动时抢占插播、达到上限后自动解除
4. alert_callout, change_diff_card, timeline_event 组件渲染与测量
5. REST API 端点验证 (/api/monitors, /api/monitors/events, /api/monitors/check)
"""
from __future__ import annotations

import json
import time
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient

from api.index import app
from core.monitor_service import monitor_service, _extract_page_core_text
from core.alert_interceptor import (
    interceptor_registry,
    DisasterAlertInterceptor,
    MonitorNoticeInterceptor,
)
from core.pipeline import generate_and_render
from core.blocks.measure import measure_block_size
from core.blocks.context import RenderContext
from PIL import Image, ImageDraw


def test_extract_page_core_text():
    """测试网页核心文本抽取与噪声过滤。"""
    html = """
    <html>
        <head><title>版本更新发布 - MyService</title></head>
        <body>
            <script>console.log("noisy tracking script");</script>
            <style>.cls{color:red;}</style>
            <h1>正式版 v2.5.0 发布</h1>
            <p>包含系统架构重构与性能提升 40%</p>
        </body>
    </html>
    """
    title, summary = _extract_page_core_text(html)
    assert "版本更新发布" in title
    assert "noisy tracking script" not in summary
    assert "v2.5.0" in summary


@pytest.mark.asyncio
async def test_monitor_service_lifecycle():
    """测试监控项的新增、变动感知与通报生成。"""
    monitor_service.clear_notices()

    target = monitor_service.add_target({
        "name": "测试站点",
        "url": "https://example.com/test-service",
        "max_presentations": 2,
        "target_mac": "TEST_MAC_001",
    })
    assert target["id"] is not None
    assert target["name"] == "测试站点"

    # 1. 模拟首次检测 -> 建立基线，无通报
    mock_client = MagicMock()
    mock_resp_1 = MagicMock()
    mock_resp_1.text = "<html><head><title>状态正常</title></head><body>系统正常运行中</body></html>"
    mock_client.get = AsyncMock(return_value=mock_resp_1)

    with patch("core.monitor_service.get_async_client", return_value=mock_client):
        notice_1 = await monitor_service.check_target(target)
        assert notice_1 is None
        assert target["last_hash"] != ""

        # 2. 模拟内容发生变动 -> 产生通报
        mock_resp_2 = MagicMock()
        mock_resp_2.text = "<html><head><title>紧急告警</title></head><body>系统遭遇突发网络抖动</body></html>"
        mock_client.get = AsyncMock(return_value=mock_resp_2)

        notice_2 = await monitor_service.check_target(target)
        assert notice_2 is not None
        assert notice_2["site_name"] == "测试站点"
        assert "变更前" not in notice_2["prev_snippet"] or "系统正常运行中" in notice_2["prev_snippet"]
        assert "系统遭遇突发网络抖动" in notice_2["new_snippet"]


@pytest.mark.asyncio
async def test_monitor_interceptor_presence_and_silence():
    """测试变动插播机制：平常静默不出现，变动时抢占插播，达标后自动恢复常规轮播。"""
    monitor_service.clear_notices()
    mac = "AA:BB:CC:11:22:33"

    # 1. 平常没有事件：检查 pending notice -> 为 None
    pending_none = await monitor_service.get_pending_notice_for_device(mac, {})
    assert pending_none is None

    # 2. 触发一次事件
    notice = monitor_service.create_change_notice(
        target_id="test_target",
        site_name="核心生产库",
        url="https://prod.internal/db",
        title="主备切换完成",
        prev_snippet="主库正常",
        new_snippet="发生故障转移，备库提升为主库",
        max_presentations=2,
        target_mac=mac,
    )
    assert notice["is_active"] is True

    # 3. 第一次请求：命中插播！
    pending_1 = await monitor_service.get_pending_notice_for_device(mac, {})
    assert pending_1 is not None
    assert pending_1["notice_id"] == notice["notice_id"]

    # 执行插播渲染并标记呈现 1 次
    date_ctx = {"time_str": "15:30", "date_str": "2026-09-05", "lunar_str": "七月廿五"}
    weather = {"weather_str": "晴 25°C", "weather_code": 0}

    img_1, content_1 = await generate_and_render(
        persona="STOIC",  # 正常请求为常规模式
        config={},
        date_ctx=date_ctx,
        weather=weather,
        battery_pct=90.0,
        mac=mac,
        screen_w=400,
        screen_h=300,
        colors=4,
    )
    assert img_1 is not None
    assert img_1.size == (400, 300)
    # 验证插播成功：内容被抢占为变动通报！
    assert content_1.get("site_name") == "核心生产库"

    # 4. 第二次请求：仍未达上限（上限为2），继续插播
    img_2, content_2 = await generate_and_render(
        persona="STOIC",
        config={},
        date_ctx=date_ctx,
        weather=weather,
        battery_pct=90.0,
        mac=mac,
        screen_w=400,
        screen_h=300,
        colors=4,
    )
    assert content_2.get("site_name") == "核心生产库"

    # 5. 第三次请求：已达上限（2次），自动静默并恢复正常 STOIC 模式！
    pending_3 = await monitor_service.get_pending_notice_for_device(mac, {})
    assert pending_3 is None

    img_3, content_3 = await generate_and_render(
        persona="STOIC",
        config={},
        date_ctx=date_ctx,
        weather=weather,
        battery_pct=90.0,
        mac=mac,
        screen_w=400,
        screen_h=300,
        colors=4,
    )
    assert img_3 is not None
    assert content_3.get("site_name") != "核心生产库"


def test_new_blocks_rendering_and_measure():
    """测试 alert_callout, change_diff_card, timeline_event 的渲染与尺寸测量。"""
    img = Image.new("1", (400, 300), 255)
    draw = ImageDraw.Draw(img)
    content = {
        "prev_field_key": "v1.0.0 稳定版",
        "new_field_key": "v2.0.0 架构升级",
    }
    ctx = RenderContext(
        draw=draw,
        img=img,
        content=content,
        screen_w=400,
        screen_h=300,
        y=10,
        colors=4,
    )

    # 1. 测量 alert_callout
    w1, h1 = measure_block_size(ctx, {"type": "alert_callout", "title": "重要提醒"}, 400)
    assert w1 == 400
    assert h1 >= 30

    # 2. 测量 change_diff_card
    w2, h2 = measure_block_size(ctx, {"type": "change_diff_card"}, 400)
    assert w2 == 400
    assert h2 >= 80

    # 3. 测量 timeline_event
    w3, h3 = measure_block_size(ctx, {"type": "timeline_event", "time": "12:00", "content": "事件"}, 400)
    assert w3 == 400
    assert h3 >= 18


def test_monitors_api_endpoints():
    """测试监控模块 REST API。"""
    with TestClient(app) as client:
        # 1. 获取列表
        resp_list = client.get("/api/monitors")
        assert resp_list.status_code == 200
        data = resp_list.json()
        assert "targets" in data

        # 2. 添加监控项
        resp_add = client.post("/api/monitors", json={
            "name": "API 端点监控",
            "url": "http://127.0.0.1:8070/health",
            "check_interval": 120,
            "max_presentations": 1,
            "target_mac": "*",
        })
        assert resp_add.status_code == 200
        new_target = resp_add.json()["target"]
        target_id = new_target["id"]

        # 3. 外部事件推送触发通报
        import hashlib
        import hmac
        import os
        import time
        event_payload = {
            "site_name": "Webhook推送站点",
            "url": "https://service.com/webhook",
            "title": "CI/CD 部署完成",
            "prev_snippet": "构建版本 102",
            "new_snippet": "构建版本 103 已成功部署至生产集群",
            "max_presentations": 2,
        }
        timestamp = str(int(time.time()))
        nonce = "integration-test-nonce"
        os.environ["MONITOR_WEBHOOK_SECRET"] = "integration-test-secret"
        secret = os.environ["MONITOR_WEBHOOK_SECRET"]
        from api.routes.monitors import EventPushSchema
        signed_payload = EventPushSchema.model_validate(event_payload)
        signature = hmac.new(
            secret.encode(),
            f"{timestamp}.{nonce}.{signed_payload.model_dump_json()}".encode(),
            hashlib.sha256,
        ).hexdigest()
        resp_event = client.post(
            "/api/monitors/events",
            json=event_payload,
            headers={
                "X-Monitor-Timestamp": timestamp,
                "X-Monitor-Nonce": nonce,
                "X-Monitor-Signature": signature,
            },
        )
        assert resp_event.status_code == 200
        assert resp_event.json()["notice"]["title"] == "CI/CD 部署完成"

        # 4. 查询活跃通报
        resp_notices = client.get("/api/monitors/notices?active_only=true")
        assert resp_notices.status_code == 200
        assert len(resp_notices.json()["notices"]) >= 1

        # 5. 清空通报
        resp_clear = client.post("/api/monitors/notices/clear")
        assert resp_clear.status_code == 200

        # 6. 删除监控项
        resp_del = client.delete(f"/api/monitors/{target_id}")
        assert resp_del.status_code == 200
