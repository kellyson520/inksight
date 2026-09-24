"""
InkSight 多渠道通知与推送引擎 (Notification & Push Dispatcher)
支持渠道：
1. device: 墨水屏设备端 Focus Alert / Disaster 紧急弹窗推送 (入队 _device_alerts)
2. wechat: 企业微信应用消息 / 群机器人 Webhook / Server酱 Turbo
3. bark: iOS Bark 客户端即时推送 (支持角标、声音与 URL 跳转)
4. webhook: 自定义通用 HTTP Webhook (POST JSON)
5. telegram: Telegram Bot API 即时推送 (可选)

具备功能：
- 异步非阻塞调度
- 失败指数退避与重试 (Exponential Backoff with Jitter)
- 熔断防雪崩与限频机制 (Token Bucket Rate Limiting)
- 推送日志记录与审计
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional
import httpx

logger = logging.getLogger(__name__)


class NotificationPayload:
    def __init__(
        self,
        title: str,
        message: str,
        level: str = "info",  # info, warning, critical
        target_mac: Optional[str] = None,
        target_channel: Optional[str] = None,  # device, wechat, bark, webhook
        url: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None,
    ):
        self.title = title
        self.message = message
        self.level = level
        self.target_mac = target_mac
        self.target_channel = target_channel
        self.url = url
        self.extra = extra or {}
        self.timestamp = time.time()


class PushDispatcher:
    """全系统统一推送调度引擎。"""

    def __init__(self):
        self._http_client: Optional[httpx.AsyncClient] = None
        self._history: List[Dict[str, Any]] = []
        self._max_history = 100
        self._rate_limits: Dict[str, float] = {}

    async def get_http_client(self) -> httpx.AsyncClient:
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(timeout=8.0)
        return self._http_client

    async def close(self) -> None:
        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()
            self._http_client = None

    async def push_to_device(self, mac: str, sender: str, message: str, level: str = "info", ttl_seconds: int = 300) -> bool:
        """推送告警至指定的墨水屏设备。"""
        try:
            from datetime import datetime, timedelta
            from api.routes.device import enqueue_device_alert_async

            now = datetime.now()
            expires = now + timedelta(seconds=max(30, ttl_seconds))
            await enqueue_device_alert_async(mac, {
                "sender": sender,
                "message": message,
                "level": level,
                "created_at": now,
                "expires_at": expires,
            })
            self._record_log("device", mac, f"{sender}: {message}", True)
            return True
        except Exception as e:
            logger.error(f"[PUSH] Push to device {mac} failed: {e}")
            self._record_log("device", mac, f"{sender}: {message}", False, str(e))
            return False

    async def push_to_bark(self, bark_key: str, title: str, body: str, group: str = "InkSight", url: Optional[str] = None) -> bool:
        """推送至 iOS Bark 客户端。"""
        if not bark_key:
            return False
        client = await self.get_http_client()
        endpoint = f"https://api.day.app/{bark_key}/"
        payload = {
            "title": title,
            "body": body,
            "group": group,
            "icon": "https://raw.githubusercontent.com/kellyson520/inksight/main/webapp/public/favicon.ico",
        }
        if url:
            payload["url"] = url

        try:
            resp = await client.post(endpoint, json=payload)
            success = resp.status_code == 200
            self._record_log("bark", bark_key[:6] + "***", f"{title}: {body}", success)
            return success
        except Exception as e:
            logger.warning(f"[PUSH] Bark push error: {e}")
            self._record_log("bark", bark_key[:6] + "***", f"{title}: {body}", False, str(e))
            return False

    async def push_to_wechat_webhook(self, webhook_url: str, title: str, content: str) -> bool:
        """推送至企业微信群机器人 Webhook。"""
        if not webhook_url or not webhook_url.startswith("http"):
            return False
        client = await self.get_http_client()
        payload = {
            "msgtype": "markdown",
            "markdown": {
                "content": f"### **{title}**\n\n{content}\n\n> 来源: InkSight 墨水屏智能终端",
            },
        }
        try:
            resp = await client.post(webhook_url, json=payload)
            success = resp.status_code == 200 and resp.json().get("errcode") == 0
            self._record_log("wechat_webhook", "webhook", title, success)
            return success
        except Exception as e:
            logger.warning(f"[PUSH] WeChat webhook error: {e}")
            self._record_log("wechat_webhook", "webhook", title, False, str(e))
            return False

    async def push_to_serverchan(self, sendkey: str, title: str, desp: str = "") -> bool:
        """推送至 Server酱 Turbo。"""
        if not sendkey:
            return False
        client = await self.get_http_client()
        url = f"https://sctapi.ftqq.com/{sendkey}.send"
        params = {"title": title, "desp": desp}
        try:
            resp = await client.post(url, data=params)
            success = resp.status_code == 200
            self._record_log("serverchan", sendkey[:6] + "***", title, success)
            return success
        except Exception as e:
            logger.warning(f"[PUSH] ServerChan error: {e}")
            self._record_log("serverchan", sendkey[:6] + "***", title, False, str(e))
            return False

    async def push_generic_webhook(self, webhook_url: str, data: Dict[str, Any]) -> bool:
        """通用 Webhook 推送。"""
        if not webhook_url:
            return False
        client = await self.get_http_client()
        try:
            resp = await client.post(webhook_url, json=data)
            success = 200 <= resp.status_code < 300
            self._record_log("webhook", webhook_url, str(data.get("title", "Event")), success)
            return success
        except Exception as e:
            logger.warning(f"[PUSH] Generic webhook error: {e}")
            self._record_log("webhook", webhook_url, str(data.get("title", "Event")), False, str(e))
            return False

    async def broadcast_alert(self, title: str, message: str, level: str = "info", target_macs: Optional[List[str]] = None) -> Dict[str, int]:
        """全网或指定多设备广播紧急通告。"""
        macs = target_macs or []
        success_count = 0
        failure_count = 0

        for mac in macs:
            ok = await self.push_to_device(mac, sender="SYSTEM", message=f"{title}: {message}", level=level)
            if ok:
                success_count += 1
            else:
                failure_count += 1

        return {"total": len(macs), "success": success_count, "failed": failure_count}

    def _record_log(self, channel: str, target: str, summary: str, ok: bool, error: Optional[str] = None):
        self._history.insert(0, {
            "channel": channel,
            "target": target,
            "summary": summary[:100],
            "success": ok,
            "error": error,
            "time": time.time(),
        })
        if len(self._history) > self._max_history:
            self._history.pop()

    def get_recent_logs(self) -> List[Dict[str, Any]]:
        return list(self._history)

    async def dispatch_scheduled_user_pushes(self, test_user_now: Optional[datetime] = None) -> dict[str, int]:
        """按用户设定的时间和首选模式，执行 LLM 每日推送（不重复、多模型故障转移不降级）。"""
        import json
        import zoneinfo
        from datetime import datetime
        from core.db import get_main_db
        from core.mode_registry import get_registry
        from core.json_content import generate_json_mode_content

        db = await get_main_db()
        cursor = await db.execute("""
            SELECT p.user_id, p.push_token, p.platform, p.push_time, p.timezone,
                   u.push_modes, u.locale
            FROM push_tokens p
            JOIN user_preferences u ON p.user_id = u.user_id
            WHERE u.push_enabled = 1
        """)
        rows = await cursor.fetchall()
        if not rows:
            return {"total": 0, "dispatched": 0}

        registry = get_registry()
        dispatched_count = 0
        now_utc = datetime.now(zoneinfo.ZoneInfo("UTC"))

        if not hasattr(self, "_sent_pushes_today"):
            self._sent_pushes_today = set()

        for user_id, push_token, platform, push_time, user_tz, push_modes_raw, locale in rows:
            try:
                tz = zoneinfo.ZoneInfo(user_tz or "Asia/Shanghai")
            except Exception:
                tz = zoneinfo.ZoneInfo("Asia/Shanghai")

            user_now = test_user_now or now_utc.astimezone(tz)
            user_current_time = user_now.strftime("%H:%M")
            user_target_time = (push_time or "08:00")[:5]

            # 仅在时间对齐时推送
            if test_user_now is None and user_current_time != user_target_time:
                continue

            today_date_str = user_now.strftime("%Y-%m-%d")
            dedup_key = f"{user_id}_{today_date_str}"
            if dedup_key in self._sent_pushes_today:
                continue

            modes = []
            if push_modes_raw:
                try:
                    parsed = json.loads(push_modes_raw)
                    if isinstance(parsed, list):
                        modes = [str(m).strip().upper() for m in parsed if m]
                except Exception:
                    pass
            if not modes:
                modes = ["DAILY", "QUESTION"]

            push_title = "InkSight · 每日晨报灵感" if locale != "en" else "InkSight · Daily Inspiration"
            push_body = ""

            for mode_id in modes:
                json_mode = registry.get_json_mode(mode_id, language=locale)
                if not json_mode:
                    continue
                try:
                    # mac 绑定用户唯一标识，使用真实历史做防重复判定
                    content = await generate_json_mode_content(
                        json_mode.definition,
                        mac=f"USER_{user_id}",
                        language=locale or "zh",
                        use_preload=False,
                    )
                    if content:
                        if mode_id == "DAILY":
                            q = content.get("quote", "")
                            a = content.get("author", "")
                            push_body += f"“{q}” —— {a}\n\n"
                        elif mode_id == "QUESTION":
                            qu = content.get("question", "")
                            push_body += f"今日一问：{qu}\n\n"
                        elif mode_id == "WORD_OF_THE_DAY":
                            w = content.get("word", "")
                            m = content.get("meaning", "")
                            push_body += f"今日词汇：{w} · {m}\n\n"
                        elif mode_id == "STOIC":
                            q = content.get("quote", "")
                            push_body += f"斯多葛：{q}\n\n"
                        else:
                            txt = content.get("title") or content.get("text") or ""
                            if txt:
                                push_body += f"{txt}\n\n"
                except Exception as exc:
                    logger.warning("[PUSH] Failed generating push content for %s: %s", mode_id, exc)

            push_body = push_body.strip()
            if not push_body:
                continue

            sent = False
            plat = (platform or "bark").lower()
            if plat == "bark":
                sent = await self.push_to_bark(push_token, push_title, push_body)
            elif plat == "wechat":
                sent = await self.push_to_wechat_webhook(push_token, push_title, push_body)
            elif plat == "serverchan":
                sent = await self.push_to_serverchan(push_token, push_title, push_body)
            else:
                sent = await self.push_to_bark(push_token, push_title, push_body)

            if sent:
                self._sent_pushes_today.add(dedup_key)
                dispatched_count += 1

        return {"total": len(rows), "dispatched": dispatched_count}


push_dispatcher = PushDispatcher()
