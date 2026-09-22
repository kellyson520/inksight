"""
测试 /api/render 端点对于设备端上报参数的容错与正确处理：
1. 传入电压 v 参数时，应通过 calc_battery_pct 正常计算电池百分比，绝不抛出 AttributeError: 'RenderQuery' object has no attribute 'b'
2. 支持 bpp 额外查询参数，不报错
"""
from fastapi.testclient import TestClient
import pytest
from unittest.mock import AsyncMock, patch
from PIL import Image
from api.index import app


def test_render_endpoint_handles_voltage_without_attribute_error():
    client = TestClient(app)
    mac = "AA:BB:CC:DD:EE:FF"

    fake_img = Image.new("1", (400, 300), 1)
    with (
        patch("api.routes.render.require_device_token", new_callable=AsyncMock),
        patch("api.routes.render.get_active_config", new_callable=AsyncMock, return_value={"refresh_interval": 10}),
        patch("api.routes.render.get_device_owner", new_callable=AsyncMock, return_value=1),
        patch(
            "api.routes.render.build_image",
            new_callable=AsyncMock,
            return_value=(fake_img, "WORD_OF_THE_DAY", False, False, False, False, False, "local"),
        ),
    ):
        # 模拟真实 ESP32 设备的请求参数
        resp = client.get(
            f"/api/render?v=3.85&mac={mac}&rssi=-45&refresh_min=10&w=400&h=300&bpp=2&colors=4",
            headers={"X-Device-Token": "test-token"},
        )
        assert resp.status_code == 200
        assert "X-Refresh-Minutes" in resp.headers
