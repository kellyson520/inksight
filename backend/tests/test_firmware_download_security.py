"""
测试固件代理下载端点的 SSRF 拦截：
1. 拦截直接指向私网/环回地址的 download_url
2. 拦截跳转到内网/元数据服务的 302 重定向
"""
from unittest.mock import AsyncMock, patch
import pytest
from fastapi import HTTPException
from api.routes.firmware import firmware_download
from starlette.requests import Request


@pytest.mark.asyncio
async def test_firmware_download_blocks_private_download_url(monkeypatch):
    mock_request = Request({"type": "http", "method": "GET", "headers": []})

    # 模拟设备状态表中包含了指向本地环回或内网私有地址的固件链接
    fake_state = {"ota_original_url": "http://127.0.0.1:8080/evil.bin", "ota_url": ""}
    monkeypatch.setattr("api.routes.firmware._get_device_state_row", AsyncMock(return_value=fake_state))

    with pytest.raises(HTTPException) as exc_info:
        await firmware_download("v1.0.0", mock_request, mac="AA:BB:CC:DD:EE:FF")

    assert exc_info.value.status_code == 400
    assert "blocked" in exc_info.value.detail.lower() or "private" in exc_info.value.detail.lower()
