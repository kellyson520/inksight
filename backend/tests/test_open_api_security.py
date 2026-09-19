"""
测试开放 API (Open API) 鉴权安全机制：
1. 已绑定设备拒绝未授权外部篡改
2. 携带有效 X-Agent-Token 的 Webhook 外部调用允许通过
"""
from unittest.mock import AsyncMock, patch
import pytest
from fastapi.testclient import TestClient
from api.index import app


def test_bound_device_rejects_unauthorized_open_api_push():
    with TestClient(app) as client:
        bound_mac = "AA:BB:CC:11:22:33"

        with patch("api.routes.open.get_device_owner", new_callable=AsyncMock, return_value=123):
            # 1. 企图篡改文本
            resp = client.post(f"/api/open/device/{bound_mac}/text", json={"message": "恶意篡改消息"})
            assert resp.status_code == 403

            # 2. 企图篡改 RSS
            resp = client.post(f"/api/open/device/{bound_mac}/rss", json={"feed_url": "https://evil.com/feed"})
            assert resp.status_code == 403

            # 3. 企图篡改 Webhook Data
            resp = client.post(f"/api/open/device/{bound_mac}/data", json={"title": "恶意篡改"})
            assert resp.status_code == 403


def test_bound_device_accepts_valid_agent_token():
    with TestClient(app) as client:
        bound_mac = "AA:BB:CC:11:22:33"

        with (
            patch("api.routes.open.get_device_owner", new_callable=AsyncMock, return_value=123),
            patch("api.routes.open.validate_alert_token", new_callable=AsyncMock, return_value=True),
        ):
            resp = client.post(
                f"/api/open/device/{bound_mac}/text",
                headers={"X-Agent-Token": "secret-agent-token-123"},
                json={"message": "授权通过的 Webhook 消息"},
            )
            assert resp.status_code == 200
            assert resp.json()["code"] == 0
