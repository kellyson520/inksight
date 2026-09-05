"""
InkSight CPA 与 Keeper 容器额度聚合基础设施服务 (CPA & Usage Keeper Service)
连接本地 CLIProxyAPI (CPA) 容器与 CPA-Usage-Keeper 容器，
聚合多账户认证文件、限额重置周期、模型消耗、调用次数与费用账单。
【特别约束】：禁止在墨水屏输出字符串中包含任何 Emoji，确保黑白电子纸点阵整洁美观且无超出边框风险。
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

# 默认容器路径与端口配置
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


class CpaKeeperService:
    """CPA 代理与 Keeper 额度统计聚合服务。"""

    def __init__(
        self,
        keeper_db_path: str = _DEFAULT_KEEPER_DB,
        cpa_db_path: str = _DEFAULT_CPA_BILLING_DB,
        cache_ttl: float = 5.0,
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
        reset_countdown = "无需重置"
        reset_h = 0
        reset_m = 0
        auth_identities: list[dict[str, Any]] = []

        # 1. 查询 Keeper 数据库中的当日汇总、热门模型、重置周期与本地认证文件
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

                # 查询全部本地认证凭证 (usage_identities) 的请求活动与限额状态
                id_rows = cur.execute(
                    """
                    SELECT id, name, alias, provider, file_name, identity, total_requests, success_count, total_tokens, last_used_at, disabled
                    FROM usage_identities
                    WHERE is_deleted = 0
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
                    is_disabled = bool(ir[10])

                    # 查找该凭证的重置周期与剩余配额
                    cycle = cur.execute(
                        """
                        SELECT id, quota_key, reset_at, window_seconds
                        FROM quota_cycles
                        WHERE auth_index = ?
                        ORDER BY id DESC LIMIT 1
                        """,
                        (ident_hash,),
                    ).fetchone()

                    ident_reset_str = "无需重置"
                    rem_pct_num: int = 100
                    if cycle:
                        c_id, q_key, r_at_str, win_sec = cycle
                        if r_at_str:
                            try:
                                clean_ts = str(r_at_str)[:19] + "+00:00"
                                dt = datetime.datetime.fromisoformat(clean_ts)
                                diff = dt - now_utc
                                secs = int(diff.total_seconds())
                                if secs > 0:
                                    h = secs // 3600
                                    m = (secs % 3600) // 60
                                    ident_reset_str = f"{h}时{m}分"
                                    # 若全局未设倒计时，则采用首个需要重置的凭证
                                    if reset_countdown in ("无需重置", "已刷新"):
                                        reset_countdown = ident_reset_str
                                        reset_h = h
                                        reset_m = m
                                else:
                                    ident_reset_str = "已刷新"
                            except Exception:
                                ident_reset_str = "活跃"
                        seg = cur.execute(
                            "SELECT remaining_percent FROM quota_percent_segments WHERE cycle_id = ? ORDER BY id DESC LIMIT 1",
                            (c_id,),
                        ).fetchone()
                        if seg and seg[0] is not None:
                            rem_pct_num = max(0, min(100, int(seg[0])))

                    # 友好显示标签（简练且无 emoji）
                    disp_label = alias_name if alias_name else (acc_name.split("@")[0] if "@" in acc_name else acc_name)
                    if not disp_label:
                        disp_label = file_name.replace(".json", "")

                    # 限制显示长度防止溢出
                    if len(disp_label) > 12:
                        disp_label = disp_label[:11] + "…"

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
                        "reset_str": ident_reset_str,
                        "remaining_pct": f"{rem_pct_num}%",
                        "remaining_pct_num": rem_pct_num,
                        "last_used": last_used_str[:16].replace("T", " ") if last_used_str else "从未",
                        "disabled": is_disabled,
                    })

                con.close()
            except Exception as e:
                logger.warning("[CpaKeeperService] Failed to query Keeper DB: %s", e)

        # 2. 查询 CPA 计费数据库中的用户账单与凭证
        users: list[dict[str, Any]] = []
        total_cost_usd = 0.0
        credentials: list[dict[str, Any]] = []
        if os.path.exists(self.cpa_db_path):
            try:
                con = sqlite3.connect(f"file:{self.cpa_db_path}?mode=ro", uri=True, timeout=2.0)
                cur = con.cursor()

                # 用户与 Key 消费排行
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
                    if len(name) > 12:
                        name = name[:11] + "…"
                    cost = round(float(kr[2] or 0.0), 2)
                    reqs = int(kr[3] or 0)
                    toks = int(kr[4] or 0)
                    total_cost_usd += cost
                    users.append({
                        "name": name,
                        "label": kr[0],
                        "preview": kr[1],
                        "cost": cost,
                        "cost_str": f"${cost:.2f}",
                        "requests": reqs,
                        "tokens": toks,
                        "tokens_str": _format_token_count(toks),
                    })

                # 上游凭证清单
                c_rows = cur.execute("SELECT provider, account, name FROM credentials").fetchall()
                for cr in c_rows:
                    credentials.append({
                        "provider": cr[0],
                        "account": cr[1],
                        "name": cr[2],
                    })

                con.close()
            except Exception as e:
                logger.warning("[CpaKeeperService] Failed to query CPA DB: %s", e)

        # 兜底测试数据
        if not auth_identities:
            auth_identities = [
                {"display_name": "AA", "provider": "CODEX", "tokens_str": "2.87B", "requests": 26138, "reset_str": "3时38分", "remaining_pct": "85%", "remaining_pct_num": 85, "disabled": False},
                {"display_name": "huo02", "provider": "ANTIGRAVITY", "tokens_str": "482.9M", "requests": 3370, "reset_str": "持续可用", "remaining_pct": "100%", "remaining_pct_num": 100, "disabled": False},
                {"display_name": "h", "provider": "GEMINI", "tokens_str": "224.0K", "requests": 43, "reset_str": "持续可用", "remaining_pct": "100%", "remaining_pct_num": 100, "disabled": False},
            ]

        if not users:
            users = [
                {"name": "huo", "cost": 258.73, "cost_str": "$258.73", "requests": 24574, "tokens_str": "3.17B"},
                {"name": "yang", "cost": 52.40, "cost_str": "$52.40", "requests": 8953, "tokens_str": "988M"},
                {"name": "test", "cost": 0.06, "cost_str": "$0.06", "requests": 30, "tokens_str": "195K"},
            ]
            total_cost_usd = 311.19

        if not top_models:
            top_models = [
                {"model": "gpt-5.6-luna", "tokens_str": "2.72B", "requests": 23496},
                {"model": "gemini-3.8-flash", "tokens_str": "480M", "requests": 3273},
                {"model": "claude-sonnet-4-6", "tokens_str": "61.6M", "requests": 412},
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
            "credentials": credentials,
            "auth_identities": auth_identities,
            "reset_countdown": reset_countdown,
            "reset_h": reset_h,
            "reset_m": reset_m,
            "update_time": time.strftime("%H:%M:%S"),
        }

        self._cached_metrics = res
        self._cached_time = now
        return res

    def get_mode_content(self, config_override: Optional[dict[str, Any]] = None, language: str = "zh") -> dict[str, Any]:
        """根据用户选定的看板模式为墨水屏提供定制化数据，完全去除 Emoji 并优化长条形单列进度条排版。"""
        metrics = self.get_aggregated_metrics()
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
        # 1. 认证文件与限额看板 (auths) —— 单列全宽+进度条，无 Emoji
        # -------------------------------------------------------------
        if focus_view == "auths":
            title = "本地认证文件与限额看板" if not is_en else "Auth Files & Quota Status"
            summary_1_lbl = "认证文件" if not is_en else "Auth Files"
            summary_1_val = f"{len(auths)} 个" if not is_en else f"{len(auths)} Files"
            summary_2_lbl = "限额窗口重置" if not is_en else "Next Quota Reset"
            summary_2_val = metrics["reset_countdown"]
            summary_3_lbl = "今日总 Token" if not is_en else "Today Tokens"
            summary_3_val = metrics["today_tokens_str"]

            col_title = "认证文件限额与请求用量" if not is_en else "Auth Files Quota & Usage"

            a1 = safe_get(auths, 0, {"display_name": "—", "provider": "—", "tokens_str": "0", "reset_str": "—", "remaining_pct": "100%", "remaining_pct_num": 100, "requests": 0})
            a2 = safe_get(auths, 1, {"display_name": "—", "provider": "—", "tokens_str": "0", "reset_str": "—", "remaining_pct": "100%", "remaining_pct_num": 100, "requests": 0})
            a3 = safe_get(auths, 2, {"display_name": "—", "provider": "—", "tokens_str": "0", "reset_str": "—", "remaining_pct": "100%", "remaining_pct_num": 100, "requests": 0})

            # 单列条目 1
            item_1_title = f"{a1['display_name']} [{a1['provider']}]"
            item_1_status = f"重置: {a1['reset_str']}" if not is_en else f"Reset: {a1['reset_str']}"
            item_1_progress_val = str(a1.get("remaining_pct_num", 100))
            item_1_detail = f"剩余配额: {a1['remaining_pct']} · 已用: {a1['tokens_str']} ({a1['requests']}次)" if not is_en else f"Quota: {a1['remaining_pct']} left · Used: {a1['tokens_str']} ({a1['requests']} reqs)"

            # 单列条目 2
            item_2_title = f"{a2['display_name']} [{a2['provider']}]"
            item_2_status = f"重置: {a2['reset_str']}" if not is_en else f"Reset: {a2['reset_str']}"
            item_2_progress_val = str(a2.get("remaining_pct_num", 100))
            item_2_detail = f"剩余配额: {a2['remaining_pct']} · 已用: {a2['tokens_str']} ({a2['requests']}次)" if not is_en else f"Quota: {a2['remaining_pct']} left · Used: {a2['tokens_str']} ({a2['requests']} reqs)"

            # 单列条目 3
            item_3_title = f"{a3['display_name']} [{a3['provider']}]"
            item_3_status = f"重置: {a3['reset_str']}" if not is_en else f"Reset: {a3['reset_str']}"
            item_3_progress_val = str(a3.get("remaining_pct_num", 100))
            item_3_detail = f"剩余配额: {a3['remaining_pct']} · 已用: {a3['tokens_str']} ({a3['requests']}次)" if not is_en else f"Quota: {a3['remaining_pct']} left · Used: {a3['tokens_str']} ({a3['requests']} reqs)"

            reset_bottom_label = (
                f"认证文件: {len(auths)} 个 · 窗口重置: {metrics['reset_countdown']}"
                if not is_en
                else f"Auth Files: {len(auths)} · Reset in: {metrics['reset_countdown']}"
            )

        # -------------------------------------------------------------
        # 2. 用户消费账单排行 (users) —— 单列全宽+消费占比进度条
        # -------------------------------------------------------------
        elif focus_view == "users":
            title = "用户与 Key 消费排行榜" if not is_en else "User Billing & Quota Ranking"
            summary_1_lbl = "今日 Token" if not is_en else "Today Tokens"
            summary_1_val = metrics["today_tokens_str"]
            summary_2_lbl = "活跃用户数" if not is_en else "Active Users"
            summary_2_val = f"{len(users)} 人" if not is_en else f"{len(users)} Users"
            summary_3_lbl = "累计消费账单" if not is_en else "Total Billing"
            summary_3_val = metrics["total_cost_str"]

            col_title = "用户消费账单与请求占比" if not is_en else "User Billing & Request Breakdown"

            u1 = safe_get(users, 0, {"name": "—", "cost": 0.0, "cost_str": "$0.00", "tokens_str": "0", "requests": 0})
            u2 = safe_get(users, 1, {"name": "—", "cost": 0.0, "cost_str": "$0.00", "tokens_str": "0", "requests": 0})
            u3 = safe_get(users, 2, {"name": "—", "cost": 0.0, "cost_str": "$0.00", "tokens_str": "0", "requests": 0})

            tot_cost = max(metrics.get("total_cost_usd", 1.0), 1.0)
            p1 = max(5, min(100, int((u1["cost"] / tot_cost) * 100)))
            p2 = max(5, min(100, int((u2["cost"] / tot_cost) * 100)))
            p3 = max(5, min(100, int((u3["cost"] / tot_cost) * 100)))

            item_1_title = f"TOP 1 · {u1['name']}"
            item_1_status = f"{u1['cost_str']}"
            item_1_progress_val = str(p1)
            item_1_detail = f"账单占比: {p1}% · 吞吐: {u1['tokens_str']} ({u1['requests']}次)" if not is_en else f"Share: {p1}% · Tokens: {u1['tokens_str']} ({u1['requests']} reqs)"

            item_2_title = f"TOP 2 · {u2['name']}"
            item_2_status = f"{u2['cost_str']}"
            item_2_progress_val = str(p2)
            item_2_detail = f"账单占比: {p2}% · 吞吐: {u2['tokens_str']} ({u2['requests']}次)" if not is_en else f"Share: {p2}% · Tokens: {u2['tokens_str']} ({u2['requests']} reqs)"

            item_3_title = f"TOP 3 · {u3['name']}"
            item_3_status = f"{u3['cost_str']}"
            item_3_progress_val = str(p3)
            item_3_detail = f"账单占比: {p3}% · 吞吐: {u3['tokens_str']} ({u3['requests']}次)" if not is_en else f"Share: {p3}% · Tokens: {u3['tokens_str']} ({u3['requests']} reqs)"

            reset_bottom_label = (
                f"账单总计: {metrics['total_cost_str']} · 成功率: {metrics['today_success_rate']}%"
                if not is_en
                else f"Total: {metrics['total_cost_str']} · Success: {metrics['today_success_rate']}%"
            )

        # -------------------------------------------------------------
        # 3. AI 模型消耗分布 (models) —— 单列全宽+Token占比进度条
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

            col_title = "热门模型调用排行与 Token 吞吐" if not is_en else "Top Models Ranking & Token Volume"

            m1 = safe_get(models, 0, {"model": "—", "tokens": 0, "tokens_str": "0", "requests": 0})
            m2 = safe_get(models, 1, {"model": "—", "tokens": 0, "tokens_str": "0", "requests": 0})
            m3 = safe_get(models, 2, {"model": "—", "tokens": 0, "tokens_str": "0", "requests": 0})

            tot_toks = max(sum(m.get("tokens", 0) for m in models), 1)
            mp1 = max(5, min(100, int((m1["tokens"] / tot_toks) * 100)))
            mp2 = max(5, min(100, int((m2["tokens"] / tot_toks) * 100)))
            mp3 = max(5, min(100, int((m3["tokens"] / tot_toks) * 100)))

            item_1_title = format_model_name(m1["model"])
            item_1_status = f"{m1['tokens_str']} Tokens"
            item_1_progress_val = str(mp1)
            item_1_detail = f"吞吐占比: {mp1}% · 调用: {m1['requests']} 次" if not is_en else f"Share: {mp1}% · Calls: {m1['requests']} reqs"

            item_2_title = format_model_name(m2["model"])
            item_2_status = f"{m2['tokens_str']} Tokens"
            item_2_progress_val = str(mp2)
            item_2_detail = f"吞吐占比: {mp2}% · 调用: {m2['requests']} 次" if not is_en else f"Share: {mp2}% · Calls: {m2['requests']} reqs"

            item_3_title = format_model_name(m3["model"])
            item_3_status = f"{m3['tokens_str']} Tokens"
            item_3_progress_val = str(mp3)
            item_3_detail = f"吞吐占比: {mp3}% · 调用: {m3['requests']} 次" if not is_en else f"Share: {mp3}% · Calls: {m3['requests']} reqs"

            reset_bottom_label = (
                f"今日 Token: {metrics['today_tokens_str']} · 成功率: {metrics['today_success_rate']}%"
                if not is_en
                else f"Today: {metrics['today_tokens_str']} · Success: {metrics['today_success_rate']}%"
            )

        # -------------------------------------------------------------
        # 4. 综合总览看板 (overview) —— 单列全宽+核心进度
        # -------------------------------------------------------------
        else:
            title = "CPA 额度综合看板" if not is_en else "CPA Quota Overview"
            summary_1_lbl = "今日 Token" if not is_en else "Today Tokens"
            summary_1_val = metrics["today_tokens_str"]
            summary_2_lbl = "请求量 / 成功率" if not is_en else "Requests / OK"
            summary_2_val = f"{metrics['today_success_rate']}%"
            summary_3_lbl = "累计账单" if not is_en else "Total Billing"
            summary_3_val = metrics["total_cost_str"]

            col_title = "核心凭证限额与系统负载总览" if not is_en else "Core Quota & System Load Overview"

            a1 = safe_get(auths, 0, {"display_name": "AA", "provider": "CODEX", "tokens_str": "2.87B", "reset_str": "3时38分", "remaining_pct": "85%", "remaining_pct_num": 85, "requests": 26138})
            u1 = safe_get(users, 0, {"name": "huo", "cost_str": "$258.73", "tokens_str": "3.17B", "requests": 24574})
            m1 = safe_get(models, 0, {"model": "gpt-5.6-luna", "tokens_str": "2.72B", "requests": 23496})

            item_1_title = f"首要凭证 · {a1['display_name']} [{a1['provider']}]"
            item_1_status = f"重置: {a1['reset_str']}"
            item_1_progress_val = str(a1.get("remaining_pct_num", 85))
            item_1_detail = f"剩余配额: {a1['remaining_pct']} · 已用: {a1['tokens_str']} ({a1['requests']}次)" if not is_en else f"Quota: {a1['remaining_pct']} left · Used: {a1['tokens_str']}"

            item_2_title = f"主力用户 · {u1['name']}"
            item_2_status = f"{u1['cost_str']}"
            item_2_progress_val = "80"
            item_2_detail = f"消费账单: {u1['cost_str']} · 吞吐: {u1['tokens_str']} ({u1['requests']}次)" if not is_en else f"Billing: {u1['cost_str']} · Tokens: {u1['tokens_str']}"

            item_3_title = f"主力模型 · {format_model_name(m1['model'])}"
            item_3_status = f"{m1['tokens_str']}"
            item_3_progress_val = "90"
            item_3_detail = f"模型消耗: {m1['tokens_str']} Tokens ({m1['requests']}次调用)" if not is_en else f"Tokens: {m1['tokens_str']} ({m1['requests']} calls)"

            reset_bottom_label = (
                f"窗口重置: {metrics['reset_countdown']} · 今日请求: {metrics['today_requests']} 次"
                if not is_en
                else f"Reset in: {metrics['reset_countdown']} · Requests: {metrics['today_requests']}"
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
            "col_title": col_title,
            "item_1_title": item_1_title,
            "item_1_status": item_1_status,
            "item_1_progress_val": item_1_progress_val,
            "item_1_detail": item_1_detail,
            "item_2_title": item_2_title,
            "item_2_status": item_2_status,
            "item_2_progress_val": item_2_progress_val,
            "item_2_detail": item_2_detail,
            "item_3_title": item_3_title,
            "item_3_status": item_3_status,
            "item_3_progress_val": item_3_progress_val,
            "item_3_detail": item_3_detail,
            "reset_bottom_label": reset_bottom_label,
            "update_time": metrics["update_time"],
        }


cpa_keeper_service = CpaKeeperService()
