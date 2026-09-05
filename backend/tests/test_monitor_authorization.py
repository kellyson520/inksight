from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException


@pytest.mark.asyncio
async def test_monitor_event_requires_authenticated_owner_for_target_device():
    from api.routes.monitors import EventPushSchema, push_event

    payload = EventPushSchema(site_name="x", new_snippet="changed", target_mac="AA:BB:CC:DD:EE:FF")
    with patch("api.routes.monitors.require_membership_access", new=AsyncMock(side_effect=HTTPException(status_code=403))):
        with pytest.raises(HTTPException) as error:
            await push_event(payload, None)
    assert error.value.status_code == 403
