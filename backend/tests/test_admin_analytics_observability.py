import pytest
from api.routes.admin_analytics import _analytics_overview_payload
from core.observability import obs


@pytest.mark.asyncio
async def test_admin_analytics_overview_includes_observability():
    obs.emit("request.completed", {"method": "GET", "route": "/api/render", "status": 200, "duration_ms": 12.0})
    payload = await _analytics_overview_payload()
    assert "observability" in payload
    obs_data = payload["observability"]
    assert "requests" in obs_data
    assert "dependencies" in obs_data
    assert "renders" in obs_data
    assert "cache" in obs_data
    assert "recent_failures" in obs_data
    assert obs_data["requests"]["total"] >= 1
