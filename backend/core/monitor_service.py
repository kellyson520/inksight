"""
网页变更与事件智能监控基础设施 (Web & Event Monitor Service)
监控指定目标网页/接口的变动，感知内容更新并生成通知事件。
事件由 Alert Interceptor 接管，在墨水屏设备上如同灾害预警般智能插播，
平常静默不出现，变动发生后插入轮播展示，展示达标后自动恢复正常循环。
【规范约束】：严禁 Emoji。
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
import time
from pathlib import Path
from typing import Any
from core.outbound_http import outbound_http

logger = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_TARGETS_FILE = _DATA_DIR / "monitor_targets.json"
_NOTICES_FILE = _DATA_DIR / "monitor_notices.json"


def get_async_client():
    """Legacy test/integration injection seam; production uses OutboundHttp."""
    return None


def _extract_page_core_text(html_text: str) -> tuple[str, str]:
    """提取网页主要标题与文本摘要，过滤动态脚本和易变噪声。"""
    # 提取 <title>
    title_match = re.search(r"<title[^>]*>(.*?)</title>", html_text, re.IGNORECASE | re.DOTALL)
    title = title_match.group(1).strip() if title_match else "网页内容"
    title = re.sub(r"\s+", " ", title)[:80]

    # 去除 script/style/svg
    cleaned = re.sub(r"<(script|style|svg)[^>]*>.*?</\1>", "", html_text, flags=re.IGNORECASE | re.DOTALL)
    # 去除所有 HTML 标签
    plain = re.sub(r"<[^>]+>", " ", cleaned)
    # 压缩空白字符
    plain = re.sub(r"\s+", " ", plain).strip()
    summary = plain[:240]
    return title, summary


class MonitorService:
    """网页变动与自定义事件监控服务。"""

    def __init__(self) -> None:
        self._targets: list[dict[str, Any]] = []
        self._notices: list[dict[str, Any]] = []
        self._device_presented_map: dict[str, dict[str, int]] = {}  # mac -> {notice_id: count}
        self._load_storage()
        self._seed_default_targets_if_empty()

    def _load_storage(self) -> None:
        try:
            if _TARGETS_FILE.exists():
                data = json.loads(_TARGETS_FILE.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    self._targets = data
        except Exception as e:
            logger.warning("[MonitorService] Failed to load targets: %s", e)

        try:
            if _NOTICES_FILE.exists():
                data = json.loads(_NOTICES_FILE.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    self._notices = data
        except Exception as e:
            logger.warning("[MonitorService] Failed to load notices: %s", e)

    def _save_storage(self) -> None:
        try:
            _DATA_DIR.mkdir(parents=True, exist_ok=True)
            _TARGETS_FILE.write_text(json.dumps(self._targets, ensure_ascii=False, indent=2), encoding="utf-8")
            _NOTICES_FILE.write_text(json.dumps(self._notices, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as e:
            logger.warning("[MonitorService] Failed to save storage: %s", e)

    def _seed_default_targets_if_empty(self) -> None:
        if not self._targets:
            # 预置一个默认示范监控项（例如监控本地 InkSight 服务状态页或常用服务）
            self._targets = [
                {
                    "id": "mon_001",
                    "name": "InkSight 服务端状态",
                    "url": "http://127.0.0.1:8070/api/modes",
                    "enabled": True,
                    "check_interval": 300,
                    "last_checked": 0,
                    "last_status": "ok",
                    "last_hash": "",
                    "last_summary": "Initial monitor seeded",
                    "max_presentations": 2,
                    "target_mac": "*",
                }
            ]
            self._save_storage()

    def list_targets(self) -> list[dict[str, Any]]:
        return list(self._targets)

    def add_target(self, target: dict[str, Any]) -> dict[str, Any]:
        item_id = target.get("id") or f"mon_{int(time.time() * 1000)}"
        new_item = {
            "id": item_id,
            "name": target.get("name") or "未命名监控",
            "url": str(target.get("url") or "").strip(),
            "enabled": bool(target.get("enabled", True)),
            "check_interval": int(target.get("check_interval", 300)),
            "last_checked": 0,
            "last_status": "pending",
            "last_hash": "",
            "last_summary": "",
            "max_presentations": int(target.get("max_presentations", 2)),
            "target_mac": str(target.get("target_mac") or "*").strip(),
        }
        # 如果存在则更新，否则追加
        existing = [t for t in self._targets if t["id"] == item_id]
        if existing:
            existing[0].update(new_item)
        else:
            self._targets.append(new_item)
        self._save_storage()
        return new_item

    def delete_target(self, target_id: str) -> bool:
        initial_len = len(self._targets)
        self._targets = [t for t in self._targets if t["id"] != target_id]
        if len(self._targets) != initial_len:
            self._save_storage()
            return True
        return False

    def list_notices(self, active_only: bool = False) -> list[dict[str, Any]]:
        if active_only:
            return [n for n in self._notices if n.get("is_active")]
        return list(self._notices)

    def clear_notices(self) -> None:
        self._notices.clear()
        self._device_presented_map.clear()
        self._save_storage()

    async def check_target(self, target: dict[str, Any]) -> dict[str, Any] | None:
        """对单个监控目标执行一次变动检测。若发生变动则创建通知。"""
        url = target.get("url", "")
        if not url or not target.get("enabled", True):
            return None

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) InkSight-WebWatcher/1.0",
        }

        try:
            injected_client = get_async_client()
            if injected_client is not None:
                resp = await injected_client.get(url, headers=headers)
                text = resp.text
            else:
                resp = outbound_http.get_text(url, headers=headers)
                text = resp.text
            target["last_checked"] = int(time.time())
            title, summary = _extract_page_core_text(text)
            curr_hash = hashlib.sha256(summary.encode("utf-8")).hexdigest()[:16]

            last_hash = target.get("last_hash") or ""
            target["last_status"] = "ok"

            if not last_hash:
                # 首次建立基线
                target["last_hash"] = curr_hash
                target["last_summary"] = summary
                self._save_storage()
                return None

            if curr_hash != last_hash:
                # 感知到变动！
                prev_snippet = target.get("last_summary", "")[:120]
                new_snippet = summary[:120]

                notice = self.create_change_notice(
                    target_id=target["id"],
                    site_name=target["name"],
                    url=url,
                    title=f"{target['name']} 内容更新",
                    prev_snippet=prev_snippet,
                    new_snippet=new_snippet,
                    max_presentations=target.get("max_presentations", 2),
                    target_mac=target.get("target_mac", "*"),
                )

                target["last_hash"] = curr_hash
                target["last_summary"] = summary
                target["last_status"] = "changed"
                self._save_storage()
                return notice

        except Exception as e:
            logger.warning("[MonitorService] Check target error for %s (%s): %s", target.get("name"), url, e)
            target["last_status"] = "error"
            self._save_storage()
            return None

        return None

    def create_change_notice(
        self,
        target_id: str,
        site_name: str,
        url: str,
        title: str,
        prev_snippet: str,
        new_snippet: str,
        max_presentations: int = 2,
        target_mac: str = "*",
    ) -> dict[str, Any]:
        """主动创建一条变动通报（支持检测器触发或 Webhook 触发）。"""
        notice_id = f"not_{int(time.time() * 1000)}"
        change_time = time.strftime("%H:%M")
        notice = {
            "notice_id": notice_id,
            "target_id": target_id,
            "site_name": site_name,
            "url": url,
            "title": title,
            "prev_snippet": prev_snippet or "无前置记录",
            "new_snippet": new_snippet or "检测到新变更",
            "change_time": change_time,
            "max_presentations": max_presentations,
            "target_mac": target_mac,
            "is_active": True,
            "created_at": int(time.time()),
        }
        # 保留最近 30 条历史通报
        self._notices.insert(0, notice)
        self._notices = self._notices[:30]
        self._save_storage()

        # 异步分发至多渠道推送系统 (PushDispatcher)
        try:
            from core.push_service import push_dispatcher
            asyncio.create_task(self._dispatch_push_notification(notice))
        except Exception as e:
            logger.debug("[MonitorService] Dispatch push task skipped: %s", e)

        return notice

    async def _dispatch_push_notification(self, notice: dict[str, Any]) -> None:
        """分发监控变动至外部推送渠道。"""
        try:
            from core.push_service import push_dispatcher
            title = f"【监控告警】{notice.get('site_name', '站点')}变动"
            msg = f"{notice.get('title', '')}\n最新内容: {notice.get('new_snippet', '')[:100]}"
            target_mac = notice.get("target_mac", "*")

            if target_mac != "*":
                await push_dispatcher.push_to_device(
                    mac=target_mac,
                    sender="MONITOR",
                    message=f"{notice.get('site_name')}: 内容发生变化",
                    level="warning",
                )
        except Exception as e:
            logger.warning("[MonitorService] Failed to dispatch push notification: %s", e)

    async def get_pending_notice_for_device(
        self,
        mac: str | None,
        config: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        """获取特定设备需要插播的活跃变更通报。"""
        # 如果全局禁用了网页监控插播
        if config and config.get("disable_web_monitor_alerts"):
            return None

        device_key = mac or "default"
        device_counts = self._device_presented_map.setdefault(device_key, {})

        for notice in self._notices:
            if not notice.get("is_active"):
                continue

            target_mac = notice.get("target_mac", "*")
            if target_mac != "*" and mac and target_mac != mac:
                continue

            nid = notice["notice_id"]
            presented = device_counts.get(nid, 0)
            max_limit = notice.get("max_presentations", 2)

            if presented < max_limit:
                return notice

        return None

    async def mark_notice_rendered(self, mac: str | None, notice_id: str | None) -> None:
        """记录该设备已呈现一次该通报。达到上限后将不再对此设备插播。"""
        if not notice_id:
            return
        device_key = mac or "default"
        device_counts = self._device_presented_map.setdefault(device_key, {})
        curr = device_counts.get(notice_id, 0) + 1
        device_counts[notice_id] = curr

        # 检查是否所有设备/目标都已达到上限
        for n in self._notices:
            if n["notice_id"] == notice_id:
                if curr >= n.get("max_presentations", 2):
                    # 如果是单设备绑定，直接标记 inactive
                    if n.get("target_mac") != "*":
                        n["is_active"] = False
                        self._save_storage()
                break

    def build_notice_mode_def(self, notice: dict[str, Any]) -> dict[str, Any]:
        """构建用于墨水屏渲染的 JSON Mode 定义。"""
        site_name = notice.get("site_name", "监控站点")
        title = notice.get("title", "检测到网页关键变动")
        url_short = notice.get("url", "")
        if len(url_short) > 38:
            url_short = url_short[:35] + "..."

        change_time = notice.get("change_time", time.strftime("%H:%M"))
        prev_snip = notice.get("prev_snippet", "")[:90]
        new_snip = notice.get("new_snippet", "")[:120]

        return {
            "mode_id": "WEB_NOTICE",
            "display_name": "变动通报",
            "cacheable": False,
            "content": {
                "site_name": site_name,
                "title": title,
                "url_short": url_short,
                "change_time": change_time,
                "prev_snippet": f"变更前: {prev_snip}",
                "new_snippet": f"现更新为: {new_snip}",
                "badge_title": "网页变动通报 · WEB WATCHER",
                "notice_status": f"已插播通报 · {change_time}",
                "footer_hint": "智能事件感知 · 展示达标后自动恢复正常循环",
            },
            "layout": {
                "body_align": "center",
                "status_bar": {
                    "line_width": 1,
                    "dashed": False,
                },
                "body": [
                  {
                    "type": "spacer",
                    "height": 6
                  },
                  {
                    "type": "alert_callout",
                    "title": "网页变动感知通报",
                    "level": "warning",
                    "tag": "WEB WATCHER",
                    "margin_x": 12,
                    "margin_bottom": 8
                  },
                  {
                    "type": "flex_row",
                    "justify": "space_between",
                    "align_items": "center",
                    "margin_x": 14,
                    "items": [
                      {
                        "type": "text",
                        "field": "site_name",
                        "font": "noto_serif_bold",
                        "font_size": 18
                      },
                      {
                        "type": "badge",
                        "field": "change_time",
                        "variant": "outline",
                        "font_size": 11,
                        "padding_x": 6,
                        "padding_y": 2,
                        "radius": 4
                      }
                    ]
                  },
                  {
                    "type": "spacer",
                    "height": 4
                  },
                  {
                    "type": "text",
                    "field": "url_short",
                    "font": "noto_serif_light",
                    "font_size": 11,
                    "align": "left",
                    "margin_x": 14
                  },
                  {
                    "type": "spacer",
                    "height": 6
                  },
                  {
                    "type": "change_diff_card",
                    "margin_x": 12,
                    "prev_field": "prev_snippet",
                    "new_field": "new_snippet",
                    "margin_bottom": 8
                  },
                  {
                    "type": "spacer",
                    "height": 4
                  },
                  {
                    "type": "text",
                    "field": "footer_hint",
                    "font": "noto_serif_light",
                    "font_size": 10,
                    "align": "center"
                  }
                ],
                "footer": {
                    "label": "事件监控通报",
                    "attribution_template": "InkSight 智能事件插播引擎"
                }
            }
        }


# 全局单例
monitor_service = MonitorService()
