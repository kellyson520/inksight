import pytest
import asyncio
from unittest.mock import patch
from PIL import Image
from core.providers.disaster_provider import generate_disaster_alert
from core.disaster_service import check_device_disaster_alert, fetch_active_alerts
from core.pipeline import generate_and_render

@pytest.mark.asyncio
async def test_disaster_alert_does_not_false_alarm_rainstorm_when_no_active_alert():
    """复现并修复：当设备轮播或日常渲染且当地无灾害时，绝不能虚构暴雨红色预警。"""
    config = {
        "city": "临沂",
        "modes": ["DISASTER_ALERT"],
    }
    # 模拟真实设备轮播，没有活跃灾害预警
    with patch("core.disaster_service.check_device_disaster_alert", return_value=None):
        result = await generate_disaster_alert(
            mode_def={"mode_id": "DISASTER_ALERT"},
            content_cfg={"type": "computed", "provider": "disaster_alert"},
            fallback={},
            config=config,
            mac="70:AF:09:75:51:84",
        )
    # 必须反映真实的平稳安全状态，绝不能显示虚假的暴雨红色预警
    assert "暴雨" not in result.get("title", ""), f"无灾害时误报了暴雨预警: {result.get('title')}"
    assert "暴雨" not in result.get("text", ""), f"无灾害时正文提到了暴雨: {result.get('text')}"
    assert "红色" not in result.get("level", "") or "无" in result.get("level", "")
    assert "平稳" in result.get("title", "") or "安全" in result.get("title", "") or "暂无" in result.get("title", "")

@pytest.mark.asyncio
async def test_disaster_service_filters_cancelled_or_expired_alerts():
    """测试灾害预警服务自动过滤已解除或过期的预警，防止误报。"""
    # 模拟和风天气返回了包含“解除”或 status='cancel' 的预警
    mock_data = {
        "warning": [
            {
                "id": "w1",
                "title": "临沂市气象台解除暴雨黄色预警信号",
                "level": "黄色",
                "typeName": "暴雨",
                "status": "cancel",
                "text": "降雨已减弱，临沂市气象台解除暴雨黄色预警信号。",
            }
        ]
    }
    with patch("core.disaster_service._qweather_has_credentials", return_value=True), \
         patch("core.disaster_service._qweather_get", return_value=mock_data), \
         patch("core.disaster_service._ALERT_CACHE", {}):
        alerts = await fetch_active_alerts(35.06, 118.34, "临沂")
        # 已解除的预警不能作为活跃预警生效
        assert len(alerts) == 0, f"已解除的预警不应被列入生效预警列表: {alerts}"

@pytest.mark.asyncio
async def test_disaster_alert_renders_cleanly_in_calm_state():
    """测试日常无灾害时，DISASTER_ALERT 模式可以优雅渲染平稳状态。"""
    with patch("core.disaster_service.check_device_disaster_alert", return_value=None):
        img, content = await generate_and_render(
            "DISASTER_ALERT",
            {},
            {"date_str": "9月14日 周一", "time_str": "12:00:00"},
            {"weather_str": "晴 22℃"},
            100,
            400,
            300,
            mac="70:AF:09:75:51:84",
        )
    assert img is not None
    assert img.size == (400, 300)
    assert "暴雨" not in content.get("title", "")
    assert "安全" in content.get("title", "") or "平稳" in content.get("title", "")
    # 验证图像有点阵内容
    data = list(img.getdata())
    assert data.count(0) > 1000
