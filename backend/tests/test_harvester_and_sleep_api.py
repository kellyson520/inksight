"""
测试预存池自成长端点与智能动态休眠 API
"""
import httpx
import pytest
from unittest.mock import AsyncMock, patch
from api.index import app


@pytest.mark.asyncio
async def test_api_preload_status_and_harvest():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # 1. 查询状态
        resp = await client.get("/api/preload/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert "target_modes" in data["status"]

        # 2. 触发补齐
        with patch("core.preload_harvester.PreloadHarvester.run_harvest_cycle", new_callable=AsyncMock, return_value={"total_added": 1}):
            resp_harvest = await client.post("/api/preload/harvest?max_per_mode=1")
            assert resp_harvest.status_code == 200
            hdata = resp_harvest.json()
            assert hdata["ok"] is True
            assert hdata["result"]["total_added"] == 1
