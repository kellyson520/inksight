from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException


@pytest.mark.asyncio
async def test_disaster_push_requires_owner_access():
    from api.routes.device import push_immediate_disaster_alert

    access = AsyncMock(side_effect=HTTPException(status_code=403))
    with patch("api.routes.device.ensure_web_or_device_access", new=access):
        with pytest.raises(HTTPException) as error:
            await push_immediate_disaster_alert("AA:BB:CC:DD:EE:FF", None)
    assert error.value.status_code == 403
    assert access.await_args.kwargs["owner_only"] is True
