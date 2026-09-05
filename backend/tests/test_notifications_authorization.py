from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException


@pytest.mark.asyncio
async def test_device_alert_requires_device_ownership():
    from api.routes.notifications import DeviceAlertPushRequest, send_device_alert

    body = DeviceAlertPushRequest(mac="AA:BB:CC:DD:EE:FF", message="test")
    with patch("api.routes.notifications.is_device_owner", new=AsyncMock(return_value=False)):
        with pytest.raises(HTTPException) as error:
            await send_device_alert(body, 42)
    assert error.value.status_code == 403


@pytest.mark.asyncio
async def test_device_alert_normalizes_mac_and_pushes_owned_device():
    from api.routes.notifications import DeviceAlertPushRequest, send_device_alert

    body = DeviceAlertPushRequest(mac="aa:bb:cc:dd:ee:ff", message="test")
    push = AsyncMock(return_value=True)
    with (
        patch("api.routes.notifications.is_device_owner", new=AsyncMock(return_value=True)),
        patch("api.routes.notifications.push_dispatcher.push_to_device", new=push),
    ):
        result = await send_device_alert(body, 42)
    assert result["mac"] == "AA:BB:CC:DD:EE:FF"
    assert push.await_args.kwargs["mac"] == "AA:BB:CC:DD:EE:FF"
