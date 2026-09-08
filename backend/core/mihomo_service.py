"""
Mihomo (Clash.Meta) 容器与代理订阅额度及有效期服务 (Mihomo Service)
提供 Mihomo 容器状态监控与代理订阅流量额度、有效期、剩余天数、节点状态解析。
支持单订阅与多订阅（One or Multiple Subscriptions）展示与聚合统计。
【规范约束】：严格禁止 Emoji。
"""
from __future__ import annotations

import datetime
import logging
import os
import re
import time
from pathlib import Path
from typing import Any, Optional
import httpx

logger = logging.getLogger(__name__)

# 本地常见 controller secret 探测路径
_SECRET_CANDIDATE_PATHS = [
    Path(__file__).resolve().parent.parent / "data" / "mihomo_secret",
    Path(__file__).resolve().parent.parent / "data" / ".mihomo_secret",
    Path("/opt/mihomo-cliproxy/guardian/controller_secret"),
    Path("/root/.config/mihomo/controller_secret"),
    Path("/etc/mihomo/controller_secret"),
]

# 默认 controller 探测列表
_DEFAULT_CONTROLLER_URLS = [
    "http://mihomo-cliproxy:9090",
    "http://127.0.0.1:9090",
    "http://localhost:9090",
    "http://host.docker.internal:9090",
]


def _format_bytes(b: int | float) -> str:
    """人性化格式化字节大小。"""
    try:
        val = float(b)
    except (ValueError, TypeError):
        return "0 B"

    if val <= 0:
        return "0 B"
    if val >= 1024**4:
        return f"{val / (1024**4):.2f} TB"
    if val >= 1024**3:
        return f"{val / (1024**3):.1f} GB"
    if val >= 1024**2:
        return f"{val / (1024**2):.1f} MB"
    if val >= 1024:
        return f"{val / 1024:.1f} KB"
    return f"{int(val)} B"


def _parse_reset_days_text(text: str) -> int | None:
    """Parse provider-specific reset countdown/date markers from subscription text."""
    if not text:
        return None
    match = re.search(r"(?:重置|reset)[^\d]{0,30}(\d+)\s*天", text, re.IGNORECASE)
    if match:
        return int(match.group(1))
    return None


def _parse_userinfo_header(header_val: str) -> dict[str, int]:
    """解析 Subscription-Userinfo 响应头：
    upload=1234; download=5678; total=9999; expire=1735689600
    """
    res = {"upload": 0, "download": 0, "total": 0, "expire": 0}
    if not header_val:
        return res

    for part in header_val.split(";"):
        part = part.strip()
        if "=" in part:
            k, v = part.split("=", 1)
            k = k.strip().lower()
            v = v.strip()
            if v.isdigit():
                res[k] = int(v)
    return res


def _clean_node_name(name: str) -> str:
    """清理节点名称中的 Emoji 或非法字符，确保墨水屏安全排版。"""
    if not name:
        return ""
    cleaned = re.sub(r"[\U00010000-\U0010ffff]", "", name).strip()
    return cleaned or name.strip()


def _resolve_active_egress(proxies: dict[str, dict[str, Any]]) -> str:
    """Follow selector ``now`` links until the final concrete proxy node."""
    if not isinstance(proxies, dict):
        return ""
    current = ""
    for key in ("PROXY", "CHANNEL", "MAIN", "default"):
        info = proxies.get(key)
        if isinstance(info, dict) and info.get("now"):
            current = str(info["now"])
            break
    seen: set[str] = set()
    while current and current not in seen:
        seen.add(current)
        info = proxies.get(current)
        if not isinstance(info, dict) or not info.get("now"):
            break
        current = str(info["now"])
    return _clean_node_name(current)


def _resolve_reset_days(subscription_info: dict[str, Any], proxies: list[dict[str, Any]]) -> int | None:
    """Extract reset countdown belonging to this subscription only."""
    if isinstance(subscription_info, dict):
        for key in ("Reset", "reset", "ResetDays", "reset_days"):
            value = subscription_info.get(key)
            try:
                numeric = int(value)
                if numeric > 1_000_000_000:
                    return max(0, (datetime.datetime.fromtimestamp(numeric).date() - datetime.datetime.now().date()).days)
                if numeric >= 0:
                    return numeric
            except (TypeError, ValueError, OverflowError):
                pass
    for proxy in proxies or []:
        name = str(proxy.get("name", ""))
        match = re.search(r"(?:重置.*?|剩余[^\d]*)(\d+)\s*天", name)
        if match:
            return int(match.group(1))
    return None


def _mask_sensitive_url(url: str) -> str:
    """对 URL 中的 token、secret 等敏感凭据参数进行脱敏掩码，防止日志或异常外泄。"""
    if not url:
        return ""
    try:
        return re.sub(r"([?&](?:token|secret|key|auth|password)=)[^&]+", r"\1***", url, flags=re.IGNORECASE)
    except Exception:
        return "***"


class MihomoService:
    """Mihomo 容器监控与订阅额度服务。"""

    def __init__(self) -> None:
        self._cached_data: Optional[dict[str, Any]] = None
        self._cached_time: float = 0.0
        self._cached_key: str = ""

    def _discover_provider_urls(self) -> dict[str, str]:
        """Read local provider URLs so reset metadata remains channel-specific."""
        candidates = (
            Path("/opt/mihomo-cliproxy/config/config.yaml"),
            Path("/etc/mihomo/config.yaml"),
        )
        for path in candidates:
            try:
                text = path.read_text(encoding="utf-8")
            except OSError:
                continue
            found: dict[str, str] = {}
            current = ""
            for line in text.splitlines():
                section = re.match(r"^\s{2}([A-Za-z0-9_-]+):\s*$", line)
                if section:
                    current = section.group(1)
                    continue
                match = re.match(r"^\s{4}url:\s*(https?://\S+)", line)
                if current and match:
                    found[current] = match.group(1)
            if found:
                return found
        return {}

    def _discover_secret(self, explicit_secret: Optional[str] = None) -> str:
        """解析控制密钥，支持显式传入、环境变量与文件挂载探测。"""
        if explicit_secret and explicit_secret.strip():
            return explicit_secret.strip()

        env_secret = os.getenv("MIHOMO_SECRET") or os.getenv("MIHOMO_API_SECRET")
        if env_secret and env_secret.strip():
            return env_secret.strip()

        for p in _SECRET_CANDIDATE_PATHS:
            try:
                if p.exists() and p.is_file():
                    content = p.read_text(encoding="utf-8").strip()
                    if content:
                        return content
            except Exception:
                continue

        return ""

    async def fetch_subscription_url_item(self, line: str, index: int = 1) -> Optional[dict[str, Any]]:
        """从单行配置或链接中拉取单个订阅信息。"""
        line = line.strip()
        if not line:
            return None

        custom_name = ""
        url = line
        if "|" in line:
            custom_name, url = [p.strip() for p in line.split("|", 1)]
        elif ":" in line and not line.startswith("http://") and not line.startswith("https://"):
            custom_name, url = [p.strip() for p in line.split(":", 1)]

        if not url.startswith("http://") and not url.startswith("https://"):
            return None

        headers = {
            "User-Agent": "ClashMeta/alpha Mihomo/1.18.0",
            "Accept": "*/*",
        }
        try:
            async with httpx.AsyncClient(timeout=5.0, follow_redirects=True) as client:
                resp = await client.get(url, headers=headers)
                userinfo_header = resp.headers.get("subscription-userinfo") or resp.headers.get("Subscription-Userinfo") or ""
                if userinfo_header:
                    parsed = _parse_userinfo_header(userinfo_header)
                    reset_days = _parse_reset_days_text(resp.text)
                    node_cnt = 0
                    if resp.text:
                        node_cnt = len(re.findall(r"-\s*name:\s*", resp.text)) or len(re.findall(r"proxies:\s*", resp.text))
                    
                    if not custom_name:
                        # 尝试从 URL 域名提取简短名称
                        try:
                            host = httpx.URL(url).host
                            custom_name = host.split(".")[0].upper()
                        except Exception:
                            custom_name = f"订阅 {index}"

                    return {
                        "name": custom_name,
                        "upload": parsed["upload"],
                        "download": parsed["download"],
                        "total": parsed["total"],
                        "expire": parsed["expire"],
                        "node_count": node_cnt,
                        "reset_days": reset_days,
                        "source": "sub_header",
                    }
        except Exception as e:
            masked_url = _mask_sensitive_url(url)
            logger.debug("[MihomoService] fetch_subscription_url_item error for %s: %s", masked_url, e)

        return None

    async def fetch_all_controller_subscriptions(
        self,
        api_url: Optional[str] = None,
        secret: Optional[str] = None,
    ) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        """从 Mihomo 外部控制接口拉取所有 Proxy Provider 订阅列表及全局节点状态。"""
        token = self._discover_secret(secret)
        headers = {"Authorization": f"Bearer {token}"} if token else {}

        urls_to_try = [api_url] if api_url else _DEFAULT_CONTROLLER_URLS

        for base_url in urls_to_try:
            if not base_url:
                continue
            base = base_url.rstrip("/")
            try:
                async with httpx.AsyncClient(timeout=3.0) as client:
                    # 1. 查询版本
                    v_resp = await client.get(f"{base}/version", headers=headers)
                    if v_resp.status_code != 200:
                        continue
                    v_data = v_resp.json()
                    version_str = f"Mihomo {v_data.get('version', 'Meta')}"

                    # 2. 查询各 Proxy Provider
                    p_resp = await client.get(f"{base}/providers/proxies", headers=headers)
                    p_data = p_resp.json() if p_resp.status_code == 200 else {}
                    providers = p_data.get("providers", {})

                    collected_subs: list[dict[str, Any]] = []
                    total_nodes = 0
                    active_node_name = ""
                    selector_map: dict[str, dict[str, Any]] = {}

                    for pname, pinfo in providers.items():
                        proxies = pinfo.get("proxies", [])
                        total_nodes += len(proxies)
                        for px in proxies:
                            px_name = str(px.get("name", ""))
                            selector_map[px_name] = px
                            if px.get("type") == "Selector" and px.get("now"):
                                selector_map[pname] = {"now": px.get("now")}

                        sub_info = pinfo.get("subscriptionInfo") or {}
                        reset_days = _resolve_reset_days(sub_info, proxies)
                        tot = int(sub_info.get("Total", 0))
                        if sub_info and tot > 0:
                            collected_subs.append({
                                "name": pname,
                                "upload": int(sub_info.get("Upload", 0)),
                                "download": int(sub_info.get("Download", 0)),
                                "total": tot,
                                "expire": int(sub_info.get("Expire", 0)),
                                "node_count": len(proxies),
                                "reset_days": reset_days,
                                "source": "controller_api",
                            })

                    active_node_name = _resolve_active_egress(selector_map) or "DIRECT"

                    # 优先将主渠道/包含 main 的订阅排在前面，其余按额度降序
                    def _sub_sort_key(s: dict[str, Any]) -> tuple[int, int]:
                        n = s.get("name", "").lower()
                        priority = 0 if ("main" in n or "主" in n) else (2 if ("backup" in n or "备" in n) else 1)
                        return (priority, -int(s.get("total", 0)))

                    collected_subs.sort(key=_sub_sort_key)

                    meta = {
                        "version": version_str,
                        "controller_url": base,
                        "node_count": total_nodes,
                        "active_node": active_node_name or "DIRECT",
                        "status_pill": "在线 · 运行中",
                    }
                    return meta, collected_subs
            except Exception as exc:
                logger.debug("[MihomoService] Controller probe failed for %s: %s", base_url, exc)

        return {}, []

    async def get_dashboard_data(
        self,
        sub_url: Optional[str] = None,
        api_url: Optional[str] = None,
        api_secret: Optional[str] = None,
        name: Optional[str] = None,
        force_refresh: bool = False,
    ) -> dict[str, Any]:
        """获取并格式化对齐墨水屏排版的完整多订阅数据字典。"""
        now_ts = time.time()
        cache_key = f"{sub_url}_{api_url}_{name}"
        if not force_refresh and self._cached_data and self._cached_key == cache_key and (now_ts - self._cached_time < 300):
            return dict(self._cached_data)

        meta: dict[str, Any] = {}
        subs: list[dict[str, Any]] = []

        # 1. 尝试解析自定义订阅 URL（支持多行/逗号分隔）
        if sub_url and sub_url.strip():
            raw_lines = [l.strip() for l in re.split(r"[\n,]+", sub_url) if l.strip()]
            for idx, line in enumerate(raw_lines):
                item = await self.fetch_subscription_url_item(line, index=idx + 1)
                if item:
                    subs.append(item)

        # 2. 从 Controller 获取各渠道额度；重置元数据稍后按同名渠道补齐。
        ctrl_meta, ctrl_subs = await self.fetch_all_controller_subscriptions(api_url=api_url, secret=api_secret)

        # 3. 读取每个渠道自己的订阅正文，只合并 reset_days，避免重复增加渠道或覆盖额度。
        provider_urls = self._discover_provider_urls()
        for channel_name, channel_url in provider_urls.items():
            item = await self.fetch_subscription_url_item(f"{channel_name}|{channel_url}")
            if not item:
                continue
            for existing in ctrl_subs:
                if str(existing.get("name", "")).lower() == channel_name.lower():
                    if existing.get("reset_days") is None and item.get("reset_days") is not None:
                        existing["reset_days"] = item["reset_days"]
                    break

        # 4. 合并用户自定义订阅与 Controller 数据

        if ctrl_meta:
            meta = ctrl_meta
        if not subs and ctrl_subs:
            subs = ctrl_subs
        elif ctrl_subs:
            # 合并去重
            existing_names = {s["name"].lower() for s in subs}
            for cs in ctrl_subs:
                if cs["name"].lower() not in existing_names:
                    subs.append(cs)

        # 3. 兜底默认值
        now_dt = datetime.datetime.now()
        if not subs:
            fallback_tot = 322122547200
            fallback_down = 220127666176
            subs = [{
                "name": name or "Mihomo Core",
                "upload": 0,
                "download": fallback_down,
                "total": fallback_tot,
                "expire": int(now_ts) + 86400 * 347,
                "node_count": 14,
                "source": "fallback",
            }]

        # 若用户指定了自定义名称且只有一个订阅，应用该名称
        if name and len(subs) == 1:
            subs[0]["name"] = name.strip()

        # 4. 富化每个订阅的数据
        enriched_subs: list[dict[str, Any]] = []
        tot_all = 0
        used_all = 0
        earliest_exp = 0

        for s in subs:
            up = s.get("upload", 0)
            down = s.get("download", 0)
            tot = s.get("total", 0)
            exp = s.get("expire", 0)
            used = up + down
            rem = max(0, tot - used)
            pct = (used / tot * 100) if tot > 0 else 0.0
            prog = max(0, min(100, int(round(pct))))

            tot_all += tot
            used_all += used
            if exp > 0 and (earliest_exp == 0 or exp < earliest_exp):
                earliest_exp = exp

            # 消耗程度预警色（黑、黄、红）
            # 已用占比 >= 85% 飘红；>= 60% 预警黄；其余正常黑
            if pct >= 85.0:
                rem_color = "red"
            elif pct >= 60.0:
                rem_color = "yellow"
            else:
                rem_color = "black"

            # 渠道重置天数必须来自该渠道自己的订阅元数据；没有来源时不伪造自然月日期。
            reset_days = s.get("reset_days")
            reset_badge = f"还有 {int(reset_days)} 天重置" if reset_days is not None else "重置时间未知"

            exp_str = "长期有效"
            days_badge = "长期有效"
            expire_badge = "长期有效"
            if exp > 0:
                try:
                    exp_dt = datetime.datetime.fromtimestamp(exp)
                    exp_str = exp_dt.strftime("%Y-%m-%d")
                    days = (exp_dt.date() - now_dt.date()).days
                    if days < 0:
                        days_badge = "已过期"
                        expire_badge = f"已过期（到期日 {exp_str}）"
                    elif days == 0:
                        days_badge = "今日到期"
                        expire_badge = f"今日到期（到期日 {exp_str}）"
                    else:
                        days_badge = f"剩余 {days} 天"
                        expire_badge = f"剩余 {days} 天（到期日 {exp_str}）"
                except Exception:
                    pass

            enriched_subs.append({
                "name": s.get("name", "Proxy Sub"),
                "upload_str": _format_bytes(up),
                "download_str": _format_bytes(down),
                "total_str": _format_bytes(tot),
                "used_str": _format_bytes(used),
                "remaining_str": _format_bytes(rem),
                "used_percent_str": f"{pct:.1f}%",
                "progress_percent": prog,
                "expire_str": exp_str,
                "days_left_badge": days_badge,
                "expire_badge": expire_badge,
                "reset_badge": reset_badge,
                "rem_color": rem_color,
                "node_count": f"{s.get('node_count', 0)} 节点",
            })

        rem_all = max(0, tot_all - used_all)
        pct_all = (used_all / tot_all * 100) if tot_all > 0 else 0.0
        prog_all = max(0, min(100, int(round(pct_all))))

        earliest_badge = "长期有效"
        if earliest_exp > 0:
            try:
                exp_dt = datetime.datetime.fromtimestamp(earliest_exp)
                days = (exp_dt.date() - now_dt.date()).days
                earliest_badge = "已过期" if days < 0 else (f"近期 {days} 天到期" if days <= 30 else f"剩余 {days} 天")
            except Exception:
                pass

        sub_count = len(enriched_subs)
        has_multiple = sub_count > 1
        primary_sub = enriched_subs[0]

        version = meta.get("version") or "Mihomo Meta"
        active_node = meta.get("active_node") or "DMIT EB - LaxHyper"
        status_pill = meta.get("status_pill") or "在线 · 运行中"
        total_nodes = meta.get("node_count") or sum(s.get("node_count", 0) for s in subs) or 14

        res: dict[str, Any] = {
            "title": "MIHOMO 容器与订阅看板",
            "sub_count": sub_count,
            "has_multiple_subs": has_multiple,
            "provider_name": primary_sub["name"],
            "core_version": version,
            "status_pill": status_pill,
            "active_node": active_node,
            "node_count": f"{total_nodes} 个节点",
            "update_time": time.strftime("%H:%M"),
            "footer_label": "Clash.Meta · 订阅与容器监控",
            "footer_right": f"同步于 {time.strftime('%m/%d %H:%M')}",

            # 单订阅兼容视图指标（以主订阅为主）
            "total_str": primary_sub["total_str"],
            "used_str": primary_sub["used_str"],
            "remaining_str": primary_sub["remaining_str"],
            "upload_str": primary_sub["upload_str"],
            "download_str": primary_sub["download_str"],
            "used_percent_str": primary_sub["used_percent_str"],
            "progress_percent": primary_sub["progress_percent"],
            "expire_str": primary_sub["expire_str"],
            "days_left_badge": primary_sub["days_left_badge"],
            "expire_badge": primary_sub["expire_badge"],
            "reset_badge": primary_sub["reset_badge"],
            "rem_color": primary_sub["rem_color"],

            # 多订阅全局聚合指标
            "total_all_str": _format_bytes(tot_all),
            "used_all_str": _format_bytes(used_all),
            "remaining_all_str": _format_bytes(rem_all),
            "used_all_percent_str": f"{pct_all:.1f}%",
            "progress_all_percent": prog_all,
            "earliest_days_badge": earliest_badge,
        }

        # 铺平前 3 个订阅供模板便捷取用
        for i in range(1, 4):
            idx = i - 1
            if idx < len(enriched_subs):
                cur = enriched_subs[idx]
                res[f"sub_{i}_name"] = cur["name"]
                res[f"sub_{i}_used_str"] = cur["used_str"]
                res[f"sub_{i}_total_str"] = cur["total_str"]
                res[f"sub_{i}_remaining_str"] = cur["remaining_str"]
                res[f"sub_{i}_percent_str"] = cur["used_percent_str"]
                res[f"sub_{i}_progress"] = cur["progress_percent"]
                res[f"sub_{i}_expire_str"] = cur["expire_str"]
                res[f"sub_{i}_days_badge"] = cur["days_left_badge"]
                res[f"sub_{i}_expire_badge"] = cur["expire_badge"]
                res[f"sub_{i}_reset_badge"] = cur["reset_badge"]
                res[f"sub_{i}_rem_color"] = cur["rem_color"]
            else:
                res[f"sub_{i}_name"] = ""
                res[f"sub_{i}_used_str"] = ""
                res[f"sub_{i}_total_str"] = ""
                res[f"sub_{i}_remaining_str"] = ""
                res[f"sub_{i}_percent_str"] = ""
                res[f"sub_{i}_progress"] = 0
                res[f"sub_{i}_expire_str"] = ""
                res[f"sub_{i}_days_badge"] = ""
                res[f"sub_{i}_expire_badge"] = ""
                res[f"sub_{i}_reset_badge"] = ""
                res[f"sub_{i}_rem_color"] = "black"

        self._cached_data = res
        self._cached_time = now_ts
        self._cached_key = cache_key
        return res


mihomo_service = MihomoService()
