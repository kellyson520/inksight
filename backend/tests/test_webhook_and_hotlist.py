import pytest
from fastapi.testclient import TestClient
from api.index import app
from core.providers import dispatch_provider


@pytest.mark.asyncio
async def test_hotlist_provider():
    mode_def = {"mode_id": "HOTLIST"}
    content_cfg = {"provider": "hotlist", "platform": "zhihu"}
    fallback = {
        "platform_title": "知乎测试热榜",
        "update_time": "12:00",
        "item_1": "1. 第一条热搜",
        "item_2": "2. 第二条热搜",
        "item_3": "3. 第三条热搜",
        "item_4": "4. 第四条热搜",
        "item_5": "5. 第五条热搜",
    }
    res = await dispatch_provider("hotlist", mode_def, content_cfg, fallback)
    assert res is not None
    assert "platform_title" in res
    assert "item_1" in res
    assert "item_2" in res


@pytest.mark.asyncio
async def test_webhook_provider():
    mode_def = {"mode_id": "WEBHOOK"}
    content_cfg = {"provider": "webhook"}
    fallback = {"title": "默认卡片", "primary_metric": "100"}
    
    # 模拟 override 覆盖
    kwargs = {
        "config": {
            "mode_overrides": {
                "WEBHOOK": {
                    "title": "服务器监控",
                    "primary_metric": "CPU 12%",
                }
            }
        }
    }
    res = await dispatch_provider("webhook", mode_def, content_cfg, fallback, **kwargs)
    assert res is not None
    assert res["title"] == "服务器监控"
    assert res["primary_metric"] == "CPU 12%"


def test_open_device_data_and_preview():
    with TestClient(app) as client:
        mac = "TEST_WEBHOOK_DEVICE"
        # 测试 POST /api/open/device/{mac}/data
        resp = client.post(
            f"/api/open/device/{mac}/data",
            json={
                "title": "跑步打卡统计",
                "primary_metric": "10.2 km",
                "primary_label": "今日晨跑里程",
                "item_1_value": "配速 5分12秒",
                "item_2_value": "心率 142 bpm",
                "item_3_value": "消耗 620 kcal",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 0
        assert data["data"]["mode"] == "WEBHOOK"

        # 验证预览接口
        prev_resp = client.get("/api/preview?persona=WEBHOOK")
        assert prev_resp.status_code == 200
        assert prev_resp.headers.get("content-type") == "image/png"

        prev_hot = client.get("/api/preview?persona=HOTLIST")
        assert prev_hot.status_code == 200
        assert prev_hot.headers.get("content-type") == "image/png"
