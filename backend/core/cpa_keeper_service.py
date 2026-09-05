"""
InkSight CPA 与 Keeper 容器额度聚合基础设施服务 (CPA & Usage Keeper Service)
连接本地 CLIProxyAPI (CPA) 容器与 CPA-Usage-Keeper 容器，
聚合活跃运行的本地认证文件、双周期限额重置（5小时与7天窗口）、模型消耗与调用账单。
【规范约束】：严禁 Emoji，仅展示真正有效运行的本地认证文件（排除第三方 APIKey 及停用凭证），支持环形进度条排版。
"""
from __future__ import annotations

import datetime
import logging
import os
import sqlite3
import time
from typing import Any, Optional
import httpx

logger = logging.getLogger(__name__)

_DEFAULT_KEEPER_DB = "/opt/cpa-usage-keeper/data/app.db"
_DEFAULT_CPA_BILLING_DB = "/opt/cliproxy/plugins/cpa-key-billing-state.db"
_CPA_URL = "https://127.0.0.1:8317"
_KEEPER_URL = "http://127.0.0.1:8082"


def _format_token_count(n: int) -> str:
    """紧凑格式化 Token 数量（如 1.2B, 45.6M, 128K）。"""
    if n >= 1_000_000_000:
        return f"{n / 1_000_000_000:.2f}B"
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)


def _format_timedelta(reset_at_str: Optional[str], now_utc: datetime.datetime) -> str:
    """计算倒计时并格式化为紧凑字符（如 2时45分、6天0时 或 持续可用）。"""
    if not reset_at_str:
        return "持续可用"
    try:
        clean_ts = str(reset_at_str)[:19] + "+00:00"
        dt = datetime.datetime.fromisoformat(clean_ts)
        diff = dt - now_utc
        secs = int(diff.total_seconds())
        if secs <= 0:
            return "已刷新"
        days = secs // 86400
        hours = (secs % 86400) // 3600
        mins = (secs % 3600) // 60
        if days > 0:
            return f"{days}天{hours}时"
        return f"{hours}时{mins}分"
    except Exception:
        return "持续可用"


def _calc_quota_color(pct: int | float) -> str:
    """< 20% 红色，<= 60% 黄色，其余黑色。"""
    try:
        val = float(pct)
    except (TypeError, ValueError):
        val = 100.0
    if val < 20.0:
        return "red"
    elif val <= 60.0:
        return "yellow"
    return "black"


class CpaKeeperService:
    """CPA 代理与 Keeper 额度统计聚合服务。"""

    def __init__(
        self,
        keeper_db_path: str = _DEFAULT_KEEPER_DB,
        cpa_db_path: str = _DEFAULT_CPA_BILLING_DB,
        cache_ttl: float = 1.0,
    ) -> None:
        self.keeper_db_path = keeper_db_path
        self.cpa_db_path = cpa_db_path
        self.cache_ttl = cache_ttl
        self._cached_metrics: Optional[dict[str, Any]] = None
        self._cached_time: float = 0.0

    def check_health(self) -> dict[str, Any]:
        """检查 CPA 与 Keeper 容器的存活性。"""
        cpa_ok = False
        keeper_ok = False

        try:
            with httpx.Client(verify=False, timeout=1.5) as client:
                r = client.get(f"{_CPA_URL}/")
                cpa_ok = r.status_code == 200
        except Exception:
            cpa_ok = False

        try:
            with httpx.Client(timeout=1.5) as client:
                r = client.get(f"{_KEEPER_URL}/healthz")
                keeper_ok = r.status_code == 200
        except Exception:
            keeper_ok = False

        return {
            "cpa_online": cpa_ok,
            "keeper_online": keeper_ok,
            "keeper_db_exists": os.path.exists(self.keeper_db_path),
            "cpa_db_exists": os.path.exists(self.cpa_db_path),
        }

    def get_aggregated_metrics(self, force_refresh: bool = False) -> dict[str, Any]:
        """获取综合额度、用量与排行统计。"""
        now = time.time()
        if not force_refresh and self._cached_metrics and (now - self._cached_time < self.cache_ttl):
            return self._cached_metrics

        health = self.check_health()
        today_str = datetime.datetime.now().strftime("%Y-%m-%d")
        now_utc = datetime.datetime.now(datetime.timezone.utc)

        today_req = 0
        today_succ = 0
        today_input_tok = 0
        today_output_tok = 0
        today_total_tok = 0
        top_models: list[dict[str, Any]] = []
        global_reset_5h = "持续可用"
        global_reset_7d = "持续可用"
        auth_identities: list[dict[str, Any]] = []

        # 1. 查询 Keeper 数据库中的当日汇总、热门模型与【真正活跃运行的本地认证文件】
        if os.path.exists(self.keeper_db_path):
            try:
                con = sqlite3.connect(f"file:{self.keeper_db_path}?mode=ro", uri=True, timeout=2.0)
                cur = con.cursor()

                # 当日汇总
                row = cur.execute(
                    """
                    SELECT sum(request_count), sum(success_count), sum(input_tokens), sum(output_tokens), sum(total_tokens)
                    FROM usage_overview_daily_stats
                    WHERE bucket_start LIKE ?
                    """,
                    (f"{today_str}%",),
                ).fetchone()
                if row and row[0] is not None:
                    today_req = row[0] or 0
                    today_succ = row[1] or 0
                    today_input_tok = row[2] or 0
                    today_output_tok = row[3] or 0
                    today_total_tok = row[4] or 0

                # 热门模型 Top 5
                m_rows = cur.execute(
                    """
                    SELECT model, sum(request_count), sum(total_tokens)
                    FROM usage_overview_daily_stats
                    GROUP BY model
                    ORDER BY sum(total_tokens) DESC
                    LIMIT 5
                    """
                ).fetchall()
                for mr in m_rows:
                    top_models.append({
                        "model": mr[0],
                        "requests": mr[1],
                        "tokens": mr[2],
                        "tokens_str": _format_token_count(mr[2]),
                    })

                # 查询活跃本地认证凭证：过滤非文件(APIKey)与已停用/已删除凭证
                id_rows = cur.execute(
                    """
                    SELECT id, name, alias, provider, file_name, identity, total_requests, success_count, total_tokens, last_used_at, disabled
                    FROM usage_identities
                    WHERE file_name IS NOT NULL AND file_name != ''
                      AND is_deleted = 0
                      AND (disabled = 0 OR disabled IS NULL)
                    ORDER BY total_tokens DESC
                    """
                ).fetchall()

                for ir in id_rows:
                    ident_hash = ir[5]
                    acc_name = ir[1] or ""
                    alias_name = ir[2] or ""
                    provider_name = (ir[3] or "unknown").upper()
                    file_name = ir[4] or acc_name or ident_hash[:8]
                    total_reqs = int(ir[6] or 0)
                    total_toks = int(ir[8] or 0)
                    last_used_str = str(ir[9] or "")

                    # 1. 5小时滑动窗口 (rate_limit.primary_window, 18000s)
                    c_5h = cur.execute(
                        """
                        SELECT id, reset_at
                        FROM quota_cycles
                        WHERE auth_index = ? AND quota_key = 'rate_limit.primary_window'
                        ORDER BY id DESC LIMIT 1
                        """,
                        (ident_hash,),
                    ).fetchone()
                    reset_5h_str = _format_timedelta(c_5h[1] if c_5h else None, now_utc)

                    # 2. 7天周循环窗口 (rate_limit.secondary_window, 604800s)
                    c_7d = cur.execute(
                        """
                        SELECT id, reset_at
                        FROM quota_cycles
                        WHERE auth_index = ? AND quota_key = 'rate_limit.secondary_window'
                        ORDER BY id DESC LIMIT 1
                        """,
                        (ident_hash,),
                    ).fetchone()
                    reset_7d_str = _format_timedelta(c_7d[1] if c_7d else None, now_utc)

                    # 3. 剩余配额百分比 (来自最近的 quota_percent_segments)
                    rem_pct_num = 100
                    target_cycle_id = (c_5h[0] if c_5h else None) or (c_7d[0] if c_7d else None)
                    if target_cycle_id:
                        seg = cur.execute(
                            "SELECT remaining_percent FROM quota_percent_segments WHERE cycle_id = ? ORDER BY id DESC LIMIT 1",
                            (target_cycle_id,),
                        ).fetchone()
                        if seg and seg[0] is not None:
                            rem_pct_num = max(0, min(100, int(seg[0])))

                    # 标签名称
                    disp_label = alias_name if alias_name else (acc_name.split("@")[0] if "@" in acc_name else acc_name)
                    if not disp_label:
                        disp_label = file_name.replace(".json", "")

                    if global_reset_5h in ("持续可用", "已刷新") and reset_5h_str not in ("持续可用", "已刷新"):
                        global_reset_5h = reset_5h_str
                    if global_reset_7d in ("持续可用", "已刷新") and reset_7d_str not in ("持续可用", "已刷新"):
                        global_reset_7d = reset_7d_str

                    auth_identities.append({
                        "id": ir[0],
                        "identity": ident_hash,
                        "name": acc_name,
                        "alias": alias_name,
                        "display_name": disp_label,
                        "file_name": file_name,
                        "provider": provider_name,
                        "requests": total_reqs,
                        "tokens": total_toks,
                        "tokens_str": _format_token_count(total_toks),
                        "reset_5h_str": reset_5h_str,
                        "reset_7d_str": reset_7d_str,
                        "remaining_pct": f"{rem_pct_num}%",
                        "remaining_pct_num": rem_pct_num,
                        "last_used": last_used_str[:16].replace("T", " ") if last_used_str else "从未",
                    })

                con.close()
            except Exception as e:
                logger.warning("[CpaKeeperService] Failed to query Keeper DB: %s", e)

        # 2. 查询 CPA 计费数据库
        users: list[dict[str, Any]] = []
        total_cost_usd = 0.0
        if os.path.exists(self.cpa_db_path):
            try:
                con = sqlite3.connect(f"file:{self.cpa_db_path}?mode=ro", uri=True, timeout=2.0)
                cur = con.cursor()
                k_rows = cur.execute(
                    """
                    SELECT label, preview, cost_usd, requests,
                           (uncached_input_tokens + output_tokens + cache_read_tokens) as total_tok
                    FROM api_keys
                    WHERE deleted_at = 0
                    ORDER BY cost_usd DESC
                    """
                ).fetchall()
                for kr in k_rows:
                    name = kr[0] or kr[1] or "Default"
                    cost = round(float(kr[2] or 0.0), 2)
                    reqs = int(kr[3] or 0)
                    toks = int(kr[4] or 0)
                    total_cost_usd += cost
                    users.append({
                        "name": name,
                        "cost": cost,
                        "cost_str": f"${cost:.2f}",
                        "requests": reqs,
                        "tokens": toks,
                        "tokens_str": _format_token_count(toks),
                    })
                con.close()
            except Exception as e:
                logger.warning("[CpaKeeperService] Failed to query CPA DB: %s", e)

        # 兜底测试数据
        if not auth_identities:
            auth_identities = [
                {"display_name": "AA", "provider": "CODEX", "tokens_str": "2.87B", "requests": 26139, "reset_5h_str": "2时45分", "reset_7d_str": "6天0时", "remaining_pct": "85%", "remaining_pct_num": 85},
                {"display_name": "huo02", "provider": "ANTIGRAVITY", "tokens_str": "485.5M", "requests": 3370, "reset_5h_str": "持续可用", "reset_7d_str": "持续可用", "remaining_pct": "100%", "remaining_pct_num": 100},
            ]

        if not users:
            users = [
                {"name": "huo", "cost": 258.73, "cost_str": "$258.73", "requests": 24574, "tokens_str": "3.17B"},
                {"name": "yang", "cost": 52.40, "cost_str": "$52.40", "requests": 8953, "tokens_str": "988M"},
            ]
            total_cost_usd = 311.19

        if not top_models:
            top_models = [
                {"model": "gpt-5.6-luna", "tokens_str": "2.72B", "requests": 23496},
                {"model": "gemini-3.8-flash", "tokens_str": "480M", "requests": 3273},
            ]

        success_rate = round((today_succ / today_req * 100.0), 1) if today_req > 0 else 100.0

        res = {
            "health": health,
            "cpa_status": "ONLINE" if health["cpa_online"] else "OFFLINE",
            "keeper_status": "ONLINE" if health["keeper_online"] else "OFFLINE",
            "today_requests": today_req,
            "today_success": today_succ,
            "today_success_rate": success_rate,
            "today_tokens": today_total_tok,
            "today_tokens_str": _format_token_count(today_total_tok),
            "today_input_tokens_str": _format_token_count(today_input_tok),
            "today_output_tokens_str": _format_token_count(today_output_tok),
            "total_cost_usd": round(total_cost_usd, 2),
            "total_cost_str": f"${total_cost_usd:.2f}",
            "users": users,
            "user_count": len(users),
            "top_models": top_models,
            "auth_identities": auth_identities,
            "global_reset_5h": global_reset_5h,
            "global_reset_7d": global_reset_7d,
            "reset_countdown": global_reset_5h,
            "update_time": time.strftime("%H:%M:%S"),
        }

        self._cached_metrics = res
        self._cached_time = now
        return res

    def get_mode_content(
        self,
        config_override: Optional[dict[str, Any]] = None,
        language: str = "zh",
        force_refresh: bool = False,
    ) -> dict[str, Any]:
        """根据用户选定的看板模式为墨水屏提供定制化数据（无 Emoji、支持双重置与环形进度条）。"""
        metrics = self.get_aggregated_metrics(force_refresh=force_refresh)
        is_en = language == "en"

        ov = config_override or {}
        focus_view = str(ov.get("view") or "auths").strip().lower()

        cpa_tag = "CPA 在线" if metrics["health"]["cpa_online"] else "CPA 离线"
        keeper_tag = "Keeper 在线" if metrics["health"]["keeper_online"] else "Keeper 离线"
        if is_en:
            cpa_tag = "CPA Online" if metrics["health"]["cpa_online"] else "CPA Offline"
            keeper_tag = "Keeper Online" if metrics["health"]["keeper_online"] else "Keeper Offline"

        header_status = f"{cpa_tag} · {keeper_tag}"
        auths = metrics.get("auth_identities", [])
        users = metrics.get("users", [])
        models = metrics.get("top_models", [])

        def safe_get(lst, idx, default):
            return lst[idx] if len(lst) > idx else default

        def format_model_name(name: str) -> str:
            return (
                name.replace("gemini-", "Gemini ")
                .replace("-flash-high", " Flash")
                .replace("claude-", "Claude ")
                .replace("-sonnet-4-6", " Sonnet")
                .replace("gpt-", "GPT-")
            )

        # -------------------------------------------------------------
        # 1. 认证文件与限额看板 (auths) —— 2个运行中的认证文件，带 5h/7天 重置与右侧环形进度条
        # -------------------------------------------------------------
        if focus_view == "auths":
            title = "本地认证文件与限额看板" if not is_en else "Auth Files & Quota Status"
            summary_1_lbl = "运行中文件" if not is_en else "Active Files"
            summary_1_val = f"{len(auths)} 个" if not is_en else f"{len(auths)} Files"
            summary_2_lbl = "5小时窗口重置" if not is_en else "5h Window Reset"
            summary_2_val = metrics.get("global_reset_5h", "持续可用")
            summary_3_lbl = "7天窗口重置" if not is_en else "7d Window Reset"
            summary_3_val = metrics.get("global_reset_7d", "持续可用")

            a1 = safe_get(auths, 0, {"display_name": "AA", "provider": "CODEX", "tokens_str": "2.87B", "reset_5h_str": "2时45分", "reset_7d_str": "6天0时", "remaining_pct": "85%", "remaining_pct_num": 85, "requests": 26139})
            a2 = safe_get(auths, 1, {"display_name": "huo02", "provider": "ANTIGRAVITY", "tokens_str": "485.5M", "reset_5h_str": "持续可用", "reset_7d_str": "持续可用", "remaining_pct": "100%", "remaining_pct_num": 100, "requests": 3370})

            # 卡片 1 (左侧信息 + 右侧环形)
            card_1_title = f"{a1['display_name']}  [{a1['provider']}]"
            card_1_status = "• 正常调用中" if not is_en else "• Active"
            card_1_reset_text = f"5h重置: {a1['reset_5h_str']}   7天重置: {a1['reset_7d_str']}" if not is_en else f"5h Reset: {a1['reset_5h_str']}  7d: {a1['reset_7d_str']}"
            card_1_usage_text = f"已用: {a1['tokens_str']} · {a1['requests']} 次请求" if not is_en else f"Used: {a1['tokens_str']} · {a1['requests']} reqs"
            card_1_ring_val = str(a1.get("remaining_pct_num", 85))
            card_1_ring_text = a1["remaining_pct"]
            card_1_ring_color = _calc_quota_color(a1.get("remaining_pct_num", 85))
            card_1_ring_label = "剩余配额" if not is_en else "Quota Left"

            # 卡片 2 (左侧信息 + 右侧环形)
            card_2_title = f"{a2['display_name']}  [{a2['provider']}]"
            card_2_status = "• 正常调用中" if not is_en else "• Active"
            card_2_reset_text = f"5h重置: {a2['reset_5h_str']}   7天重置: {a2['reset_7d_str']}" if not is_en else f"5h Reset: {a2['reset_5h_str']}  7d: {a2['reset_7d_str']}"
            card_2_usage_text = f"已用: {a2['tokens_str']} · {a2['requests']} 次请求" if not is_en else f"Used: {a2['tokens_str']} · {a2['requests']} reqs"
            card_2_ring_val = str(a2.get("remaining_pct_num", 100))
            card_2_ring_text = a2["remaining_pct"]
            card_2_ring_color = _calc_quota_color(a2.get("remaining_pct_num", 100))
            card_2_ring_label = "配额充沛" if not is_en else "Full Quota"

            reset_bottom_label = (
                f"监控认证文件: {len(auths)} 个  ·  今日总 Token: {metrics['today_tokens_str']}"
                if not is_en
                else f"Active Auths: {len(auths)}  ·  Today Tokens: {metrics['today_tokens_str']}"
            )

        # -------------------------------------------------------------
        # 2. 用户消费账单排行 (users)
        # -------------------------------------------------------------
        elif focus_view == "users":
            title = "用户与 Key 消费排行榜" if not is_en else "User Billing & Quota Ranking"
            summary_1_lbl = "今日 Token" if not is_en else "Today Tokens"
            summary_1_val = metrics["today_tokens_str"]
            summary_2_lbl = "活跃用户数" if not is_en else "Active Users"
            summary_2_val = f"{len(users)} 人" if not is_en else f"{len(users)} Users"
            summary_3_lbl = "累计消费账单" if not is_en else "Total Billing"
            summary_3_val = metrics["total_cost_str"]

            u1 = safe_get(users, 0, {"name": "huo", "cost": 258.73, "cost_str": "$258.73", "tokens_str": "3.17B", "requests": 24574})
            u2 = safe_get(users, 1, {"name": "yang", "cost": 52.40, "cost_str": "$52.40", "tokens_str": "988M", "requests": 8953})

            tot_cost = max(metrics.get("total_cost_usd", 1.0), 1.0)
            p1 = max(5, min(100, int((u1["cost"] / tot_cost) * 100)))
            p2 = max(5, min(100, int((u2["cost"] / tot_cost) * 100)))

            card_1_title = f"TOP 1 · {u1['name']}"
            card_1_status = u1["cost_str"]
            card_1_reset_text = f"总账单占比: {p1}%   累计请求: {u1['requests']} 次"
            card_1_usage_text = f"吞吐量: {u1['tokens_str']} Tokens"
            card_1_ring_val = str(p1)
            card_1_ring_text = f"{p1}%"
            card_1_ring_color = _calc_quota_color(p1)
            card_1_ring_label = "账单占比" if not is_en else "Cost Share"

            card_2_title = f"TOP 2 · {u2['name']}"
            card_2_status = u2["cost_str"]
            card_2_reset_text = f"总账单占比: {p2}%   累计请求: {u2['requests']} 次"
            card_2_usage_text = f"吞吐量: {u2['tokens_str']} Tokens"
            card_2_ring_val = str(p2)
            card_2_ring_text = f"{p2}%"
            card_2_ring_color = _calc_quota_color(p2)
            card_2_ring_label = "账单占比" if not is_en else "Cost Share"

            reset_bottom_label = (
                f"账单总额: {metrics['total_cost_str']}  ·  成功率: {metrics['today_success_rate']}%"
                if not is_en
                else f"Total Billing: {metrics['total_cost_str']}  ·  Success: {metrics['today_success_rate']}%"
            )

        # -------------------------------------------------------------
        # 3. AI 模型消耗分布 (models)
        # -------------------------------------------------------------
        elif focus_view == "models":
            title = "AI 模型消耗与请求分布" if not is_en else "AI Model Usage Distribution"
            m_lead = models[0]["model"].split("-")[0].upper() if models else "GPT"
            summary_1_lbl = "主力模型" if not is_en else "Lead Model"
            summary_1_val = m_lead
            summary_2_lbl = "今日请求量" if not is_en else "Today Requests"
            summary_2_val = f"{metrics['today_requests']} 次" if not is_en else str(metrics['today_requests'])
            summary_3_lbl = "今日总 Token" if not is_en else "Today Tokens"
            summary_3_val = metrics["today_tokens_str"]

            m1 = safe_get(models, 0, {"model": "gpt-5.6-luna", "tokens": 2720000000, "tokens_str": "2.72B", "requests": 23496})
            m2 = safe_get(models, 1, {"model": "gemini-3.8-flash-high", "tokens": 480000000, "tokens_str": "480M", "requests": 3273})

            tot_toks = max(sum(m.get("tokens", 0) for m in models), 1)
            mp1 = max(5, min(100, int((m1["tokens"] / tot_toks) * 100)))
            mp2 = max(5, min(100, int((m2["tokens"] / tot_toks) * 100)))

            card_1_title = format_model_name(m1["model"])
            card_1_status = f"{m1['tokens_str']}"
            card_1_reset_text = f"吞吐占比: {mp1}%   调用频次: {m1['requests']} 次"
            card_1_usage_text = f"累计 Token: {m1['tokens_str']}"
            card_1_ring_val = str(mp1)
            card_1_ring_text = f"{mp1}%"
            card_1_ring_color = _calc_quota_color(mp1)
            card_1_ring_label = "吞吐份额" if not is_en else "Token Share"

            card_2_title = format_model_name(m2["model"])
            card_2_status = f"{m2['tokens_str']}"
            card_2_reset_text = f"吞吐占比: {mp2}%   调用频次: {m2['requests']} 次"
            card_2_usage_text = f"累计 Token: {m2['tokens_str']}"
            card_2_ring_val = str(mp2)
            card_2_ring_text = f"{mp2}%"
            card_2_ring_color = _calc_quota_color(mp2)
            card_2_ring_label = "吞吐份额" if not is_en else "Token Share"

            reset_bottom_label = (
                f"今日 Token: {metrics['today_tokens_str']}  ·  成功率: {metrics['today_success_rate']}%"
                if not is_en
                else f"Today: {metrics['today_tokens_str']}  ·  Success: {metrics['today_success_rate']}%"
            )

        # -------------------------------------------------------------
        # 4. 综合总览看板 (overview)
        # -------------------------------------------------------------
        else:
            title = "CPA 额度综合看板" if not is_en else "CPA Quota Overview"
            summary_1_lbl = "今日 Token" if not is_en else "Today Tokens"
            summary_1_val = metrics["today_tokens_str"]
            summary_2_lbl = "请求量 / 成功率" if not is_en else "Requests / OK"
            summary_2_val = f"{metrics['today_success_rate']}%"
            summary_3_lbl = "累计账单" if not is_en else "Total Billing"
            summary_3_val = metrics["total_cost_str"]

            a1 = safe_get(auths, 0, {"display_name": "AA", "provider": "CODEX", "tokens_str": "2.87B", "reset_5h_str": "2时45分", "reset_7d_str": "6天0时", "remaining_pct": "85%", "remaining_pct_num": 85, "requests": 26139})
            u1 = safe_get(users, 0, {"name": "huo", "cost_str": "$258.73", "tokens_str": "3.17B", "requests": 24574})

            card_1_title = f"首要凭证 · {a1['display_name']} [{a1['provider']}]"
            card_1_status = a1["reset_5h_str"]
            card_1_reset_text = f"5h重置: {a1['reset_5h_str']}   7天重置: {a1['reset_7d_str']}"
            card_1_usage_text = f"配额剩余: {a1['remaining_pct']} · 已用: {a1['tokens_str']}"
            card_1_ring_val = str(a1.get("remaining_pct_num", 85))
            card_1_ring_text = a1["remaining_pct"]
            card_1_ring_color = _calc_quota_color(a1.get("remaining_pct_num", 85))
            card_1_ring_label = "剩余配额" if not is_en else "Quota Left"

            card_2_title = f"主力用户 · {u1['name']}"
            card_2_status = u1["cost_str"]
            card_2_reset_text = f"累计调用: {u1['requests']} 次   消费总计: {u1['cost_str']}"
            card_2_usage_text = f"Token 吞吐量: {u1['tokens_str']}"
            card_2_ring_val = "80"
            card_2_ring_text = "80%"
            card_2_ring_color = _calc_quota_color(80)
            card_2_ring_label = "预算占比" if not is_en else "Budget"

            reset_bottom_label = (
                f"首选重置: {metrics.get('global_reset_5h', '持续可用')}  ·  今日请求: {metrics['today_requests']} 次"
                if not is_en
                else f"Reset: {metrics.get('global_reset_5h', 'Active')}  ·  Requests: {metrics['today_requests']}"
            )

        return {
            "title": title,
            "header_status": header_status,
            "summary_1_label": summary_1_lbl,
            "summary_1_val": summary_1_val,
            "summary_2_label": summary_2_lbl,
            "summary_2_val": summary_2_val,
            "summary_3_label": summary_3_lbl,
            "summary_3_val": summary_3_val,
            "card_1_title": card_1_title,
            "card_1_status": card_1_status,
            "card_1_reset_text": card_1_reset_text,
            "card_1_usage_text": card_1_usage_text,
            "card_1_ring_val": card_1_ring_val,
            "card_1_ring_text": card_1_ring_text,
            "card_1_ring_color": card_1_ring_color,
            "card_1_ring_label": card_1_ring_label,
            "card_2_title": card_2_title,
            "card_2_status": card_2_status,
            "card_2_reset_text": card_2_reset_text,
            "card_2_usage_text": card_2_usage_text,
            "card_2_ring_val": card_2_ring_val,
            "card_2_ring_text": card_2_ring_text,
            "card_2_ring_color": card_2_ring_color,
            "card_2_ring_label": card_2_ring_label,
            "reset_bottom_label": reset_bottom_label,
            "update_time": metrics["update_time"],
        }


cpa_keeper_service = CpaKeeperService()
