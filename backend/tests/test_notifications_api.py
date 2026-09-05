"""
通知推送 API 端点集成测试 (Notification Endpoints Test)
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient, ASGITransport
from api.index import app
from core.auth import create_session_token


@pytest.mark.asyncio
async def test_notifications_device_alert_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. 匿名访问被拒绝 (401)
        resp = await client.post(
            "/api/notifications/device-alert",
            json={"mac": "70:AF:09:75:51:84", "message": "Test message"},
        )
        assert resp.status_code == 401

        # 2. 用户授权访问成功 (200)
        token = create_session_token(user_id=1, username="testuser")
        cookies = {"ink_session": token}
        resp = await client.post(
            "/api/notifications/device-alert",
            json={"mac": "70:AF:09:75:51:84", "sender": "ALICE", "message": "Deploy ready", "level": "info"},
            cookies=cookies,
        )
        assert resp.status_code == 200
        assert resp.json()["ok"] is True
        assert resp.json()["mac"] == "70:AF:09:75:51:84"


@pytest.mark.asyncio
async def test_notifications_bark_and_wechat_endpoints():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = create_session_token(user_id=1, username="testuser")
        cookies = {"ink_session": token}

        resp = await client.post(
            "/api/notifications/bark",
            json={"bark_key": "dummy_key", "title": "Test Bark", "body": "Hello"},
            cookies=cookies,
        )
        assert resp.status_code == 200

        resp = await client.post(
            "/api/notifications/wechat-webhook",
            json={"webhook_url": "https://qyapi.weixin.qq.com/dummy", "title": "WeChat", "content": "Body"},
            cookies=cookies,
        )
        assert resp.status_code == 200
