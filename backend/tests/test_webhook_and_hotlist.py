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

        # 验证 HOTLIST 多平台预览
        import json, urllib.parse
        ov = json.dumps({"platforms": ["weibo", "zhihu"]})
        prev_multi = client.get(f"/api/preview?persona=HOTLIST&mode_override={urllib.parse.quote(ov)}")
        assert prev_multi.status_code == 200
        assert prev_multi.headers.get("content-type") == "image/png"

        # 验证 DISASTER_ALERT 预警模式预览
        prev_dis = client.get("/api/preview?persona=DISASTER_ALERT")
        assert prev_dis.status_code == 200
        assert prev_dis.headers.get("content-type") == "image/png"


@pytest.mark.asyncio
async def test_hotlist_multi_platform_aggregation():
    from core.hotlist_service import hotlist_service

    # 1. 多平台多选获取
    res = await hotlist_service.get_multi_hotlist(["weibo", "zhihu", "bilibili"], limit=5)
    assert res is not None
    assert "items" in res
    assert len(res["items"]) >= 3
    # 确认存在多源标签
    titles = [it["title"] for it in res["items"]]
    tags = [t[:4] for t in titles if "[" in t]
    assert len(tags) > 0

    # 2. 单平台获取微博
    res_wb = await hotlist_service.get_hotlist("weibo", limit=5)
    assert res_wb is not None
    assert "微博" in res_wb["platform_title"]
    assert len(res_wb["items"]) >= 3


@pytest.mark.asyncio
async def test_disaster_alert_provider_and_catalog():
    from core.mode_catalog import builtin_catalog_map

    # 确认在 BUILTIN_CATALOG 中已注册 DISASTER_ALERT
    cat = builtin_catalog_map()
    assert "DISASTER_ALERT" in cat
    assert "预警" in cat["DISASTER_ALERT"].zh.name

    # 确认 provider 执行
    res = await dispatch_provider(
        "disaster_alert",
        {"mode_id": "DISASTER_ALERT"},
        {"provider": "disaster_alert", "level": "橙色", "hazard": "台风"},
        {},
    )
    assert res is not None
    assert res["level"] == "橙色"
    assert res["type_name"] == "台风"
    assert "台风" in res["title"]
    assert len(res["advice"]) >= 1
