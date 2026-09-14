import pytest
import asyncio
from unittest.mock import patch
from PIL import Image
from core.providers.disaster_provider import generate_disaster_alert
from core.disaster_service import check_device_disaster_alert, fetch_active_alerts
from core.pipeline import generate_and_render
from api.shared import choose_persona_from_config, advance_to_next_mode, resolve_mode

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
        assert len(alerts) == 0, f"已解除的预警不应被列入生效预警列表: {alerts}"

@pytest.mark.asyncio
async def test_silent_skip_disaster_alert_in_rotation_when_no_active_disaster():
    """测试用户要求：当没有活跃自然灾害时，轮播队列中应静默跳过 DISASTER_ALERT，不打扰用户。"""
    mac = "70:AF:09:75:51:84"
    config = {
        "mac": mac,
        "city": "临沂",
        "modes": ["WEATHER", "DISASTER_ALERT", "DAILY"],
        "refresh_strategy": "cycle",
    }
    # 1. 模拟无灾害时：轮播应当静默跳过 DISASTER_ALERT，只在 WEATHER 和 DAILY 之间轮换
    with patch("core.disaster_service.check_device_disaster_alert", return_value=None):
        selected_modes = []
        for _ in range(6):
            persona = await choose_persona_from_config(config, mac=mac)
            selected_modes.append(persona)
        assert "DISASTER_ALERT" not in selected_modes, f"无灾害时 DISASTER_ALERT 应该静默跳过，但被选中了: {selected_modes}"
        assert set(selected_modes) == {"WEATHER", "DAILY"}

    # 2. 模拟当确实有灾害（或模拟报警）时，DISASTER_ALERT 恢复正常轮播
    active_alert = {
        "title": "临沂市气象台台风黄色预警",
        "level": "黄色",
        "type_name": "台风",
        "severity_score": 2,
    }
    with patch("core.disaster_service.check_device_disaster_alert", return_value=active_alert):
        selected_modes_with_alert = []
        for _ in range(6):
            persona = await choose_persona_from_config(config, mac=mac)
            selected_modes_with_alert.append(persona)
        assert "DISASTER_ALERT" in selected_modes_with_alert, "有灾害时应当能够轮播到 DISASTER_ALERT"

@pytest.mark.asyncio
async def test_resolve_mode_silently_skips_disaster_alert_for_device_when_calm():
    """测试设备 resolve_mode：即使请求被导向 DISASTER_ALERT，若无灾害也应静默切换到常规模式。"""
    mac = "70:AF:09:75:51:84"
    config = {
        "mac": mac,
        "city": "临沂",
        "modes": ["WEATHER", "DISASTER_ALERT", "DAILY"],
        "refresh_strategy": "cycle",
    }
    with patch("core.disaster_service.check_device_disaster_alert", return_value=None):
        # 即使 persona_override 为 DISASTER_ALERT，若是设备端请求且无灾害，静默跳过
        resolved = await resolve_mode(mac, config, persona_override="DISASTER_ALERT", is_device_request=True)
        assert resolved != "DISASTER_ALERT", f"设备请求在无灾害时不应渲染 DISASTER_ALERT: {resolved}"
        assert resolved in ["WEATHER", "DAILY"]
