"""
统一事件拦截与插播通知基础设施 (Alert & Event Interceptor Engine)
为墨水屏渲染管线提供类似灾害预警、网页变动、重要事件的条件抢占与插播能力。
平常静默无感知，一旦事件触发立即插入或抢占展示，展示完毕或确认后自动恢复常规轮播。
【排版约束】：严禁 Emoji。
"""
from __future__ import annotations

import logging
from typing import Any, Protocol, runtime_checkable
from PIL import Image

from core.config import DEFAULT_LANGUAGE
from core.json_renderer import render_json_mode

logger = logging.getLogger(__name__)


@runtime_checkable
class Interceptor(Protocol):
    """插播拦截器接口协议。"""

    name: str
    priority: int  # 优先级数值越小，执行越靠前（例如 10 为灾害预警，20 为网页变动通报）

    async def check(
        self,
        mac: str | None,
        config: dict[str, Any] | None,
        persona: str,
        date_ctx: dict[str, Any],
        weather: dict[str, Any],
        battery_pct: float | None = None,
        screen_w: int = 400,
        screen_h: int = 300,
        colors: int = 2,
    ) -> tuple[Image.Image, dict[str, Any]] | None:
        """检查是否有活跃的抢占/插播事件。若有则返回 (Image, content)，无则返回 None。"""
        ...


class DisasterAlertInterceptor:
    """自然灾害最高优先级抢占拦截器。"""

    name = "disaster_alert"
    priority = 10

    async def check(
        self,
        mac: str | None,
        config: dict[str, Any] | None,
        persona: str,
        date_ctx: dict[str, Any],
        weather: dict[str, Any],
        battery_pct: float | None = None,
        screen_w: int = 400,
        screen_h: int = 300,
        colors: int = 2,
    ) -> tuple[Image.Image, dict[str, Any]] | None:
        if persona == "DISASTER_ALERT":
            return None
        if not (mac or (config and config.get("disaster_alert"))):
            return None

        try:
            from core.disaster_service import check_device_disaster_alert, build_disaster_alert_mode_def
            active_alert = await check_device_disaster_alert(mac, config)
            if not active_alert:
                return None

            logger.warning(
                "[Interceptor] DISASTER ALERT INTERRUPT for %s: %s [%s]",
                mac or "anon", active_alert.get("title"), active_alert.get("level")
            )
            mode_def = build_disaster_alert_mode_def(active_alert)
            date_str = date_ctx.get("date_str", "")
            img = render_json_mode(
                mode_def,
                mode_def.get("content") or {},
                date_str=date_str,
                weather_str=weather.get("weather_str", ""),
                battery_pct=battery_pct,
                screen_w=screen_w,
                screen_h=screen_h,
                colors=colors,
            )
            return img, mode_def.get("content") or {}
        except Exception as e:
            logger.warning("[Interceptor] Disaster check error: %s", e, exc_info=True)
            return None


class MonitorNoticeInterceptor:
    """网页变更与智能监控通报插播拦截器。"""

    name = "monitor_notice"
    priority = 20

    async def check(
        self,
        mac: str | None,
        config: dict[str, Any] | None,
        persona: str,
        date_ctx: dict[str, Any],
        weather: dict[str, Any],
        battery_pct: float | None = None,
        screen_w: int = 400,
        screen_h: int = 300,
        colors: int = 2,
    ) -> tuple[Image.Image, dict[str, Any]] | None:
        if persona == "WEB_NOTICE":
            return None

        try:
            from core.monitor_service import monitor_service
            # 检查该设备是否有未读的网页变动通知待插播
            notice = await monitor_service.get_pending_notice_for_device(mac, config)
            if not notice:
                return None

            logger.info(
                "[Interceptor] MONITOR NOTICE INTERRUPT for %s: %s -> %s",
                mac or "anon", notice.get("title"), notice.get("site_name")
            )
            mode_def = monitor_service.build_notice_mode_def(notice)
            date_str = date_ctx.get("date_str", "")
            img = render_json_mode(
                mode_def,
                notice,
                date_str=date_str,
                weather_str=weather.get("weather_str", ""),
                battery_pct=battery_pct,
                screen_w=screen_w,
                screen_h=screen_h,
                colors=colors,
            )
            # 记录一次已呈现（增加展示计数，达到上限后自动解除插播）
            await monitor_service.mark_notice_rendered(mac, notice.get("notice_id"))
            return img, notice
        except Exception as e:
            logger.warning("[Interceptor] Monitor notice check error: %s", e, exc_info=True)
            return None


class InterceptorRegistry:
    """拦截器注册与调度中心。"""

    def __init__(self) -> None:
        self._interceptors: list[Interceptor] = [
            DisasterAlertInterceptor(),
            MonitorNoticeInterceptor(),
        ]
        self._sort()

    def _sort(self) -> None:
        self._interceptors.sort(key=lambda item: item.priority)

    def register(self, interceptor: Interceptor) -> None:
        self._interceptors.append(interceptor)
        self._sort()

    def list_interceptors(self) -> list[str]:
        return [f"{i.name}(priority={i.priority})" for i in self._interceptors]

    async def execute_interceptors(
        self,
        mac: str | None,
        config: dict[str, Any] | None,
        persona: str,
        date_ctx: dict[str, Any],
        weather: dict[str, Any],
        battery_pct: float | None = None,
        screen_w: int = 400,
        screen_h: int = 300,
        colors: int = 2,
    ) -> tuple[Image.Image, dict[str, Any]] | None:
        for it in self._interceptors:
            res = await it.check(
                mac=mac,
                config=config,
                persona=persona,
                date_ctx=date_ctx,
                weather=weather,
                battery_pct=battery_pct,
                screen_w=screen_w,
                screen_h=screen_h,
                colors=colors,
            )
            if res is not None:
                return res
        return None


# 全局单例
interceptor_registry = InterceptorRegistry()
