"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Gauge, CheckCircle2, XCircle, Users, Cpu, Clock, DollarSign, Activity } from "lucide-react";

interface CpaQuotaConfigProps {
  initialView?: string;
  locale: string;
  previewLoading: boolean;
  onClose: () => void;
  onSubmit: (override: Record<string, unknown>) => Promise<void>;
}

export function CpaQuotaConfig({
  initialView = "overview",
  locale,
  previewLoading,
  onClose,
  onSubmit,
}: CpaQuotaConfigProps) {
  const [view, setView] = useState(initialView);
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState<Record<string, any> | null>(null);

  useEffect(() => {
    fetch("/api/cpa-keeper/overview")
      .then((res) => res.json())
      .then((d) => {
        if (d.success && d.data) {
          setStats(d.data);
        }
      })
      .catch((err) => console.warn("Failed to fetch CPA/Keeper stats", err))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="space-y-4">
      <div className="text-xs text-ink-light leading-relaxed">
        {locale === "zh"
          ? "实时聚合本地 Docker 中的 CLIProxyAPI (CPA) 代理与 CPA-Usage-Keeper 容器，在墨水屏上清晰呈现今日 Token 吞吐、用户消费账单、模型调用排行与速率窗口重置倒计时！"
          : "Real-time aggregation of local CPA and Keeper containers: monitor token usage, user billing, model rankings, and rate limit reset windows on your e-ink screen."}
      </div>

      {/* 容器探针状态 */}
      <div className="grid grid-cols-2 gap-2">
        <div className="p-2.5 rounded-sm border border-ink/15 bg-paper-light flex items-center justify-between">
          <div className="flex items-center gap-1.5 text-xs font-semibold text-ink">
            <Activity size={14} className="text-ink" />
            <span>CLIProxyAPI (8317)</span>
          </div>
          {stats?.health?.cpa_online ? (
            <span className="flex items-center gap-1 text-[10px] text-emerald-800 bg-emerald-100/90 px-1.5 py-0.5 rounded-xs font-semibold">
              <CheckCircle2 size={10} /> {locale === "zh" ? "运行正常" : "ONLINE"}
            </span>
          ) : (
            <span className="flex items-center gap-1 text-[10px] text-amber-800 bg-amber-100/90 px-1.5 py-0.5 rounded-xs font-semibold">
              <XCircle size={10} /> {locale === "zh" ? "未连接" : "OFFLINE"}
            </span>
          )}
        </div>

        <div className="p-2.5 rounded-sm border border-ink/15 bg-paper-light flex items-center justify-between">
          <div className="flex items-center gap-1.5 text-xs font-semibold text-ink">
            <Gauge size={14} className="text-ink" />
            <span>Usage Keeper (8082)</span>
          </div>
          {stats?.health?.keeper_online ? (
            <span className="flex items-center gap-1 text-[10px] text-emerald-800 bg-emerald-100/90 px-1.5 py-0.5 rounded-xs font-semibold">
              <CheckCircle2 size={10} /> {locale === "zh" ? "运行正常" : "ONLINE"}
            </span>
          ) : (
            <span className="flex items-center gap-1 text-[10px] text-amber-800 bg-amber-100/90 px-1.5 py-0.5 rounded-xs font-semibold">
              <XCircle size={10} /> {locale === "zh" ? "未连接" : "OFFLINE"}
            </span>
          )}
        </div>
      </div>

      {/* 实时核心数据指标 */}
      {stats ? (
        <div className="p-3 rounded-sm border border-ink/20 bg-white space-y-2">
          <div className="grid grid-cols-3 gap-2 text-center">
            <div>
              <div className="text-[10px] text-ink-light">{locale === "zh" ? "今日 Token 消耗" : "Today Tokens"}</div>
              <div className="text-sm font-bold text-ink font-mono mt-0.5">{stats.today_tokens_str || "0"}</div>
            </div>
            <div>
              <div className="text-[10px] text-ink-light">{locale === "zh" ? "今日请求 / 成功率" : "Requests / Success"}</div>
              <div className="text-sm font-bold text-ink font-mono mt-0.5">
                {stats.today_requests} <span className="text-[11px] font-normal text-emerald-700 font-sans">({stats.today_success_rate})</span>
              </div>
            </div>
            <div>
              <div className="text-[10px] text-ink-light">{locale === "zh" ? "累计消费总计" : "Total Spent"}</div>
              <div className="text-sm font-bold text-ink font-mono mt-0.5">{stats.total_cost_str || "$0.00"}</div>
            </div>
          </div>

          <div className="border-t border-ink/10 pt-2 flex items-center justify-between text-[11px] text-ink-light">
            <div className="flex items-center gap-1">
              <Clock size={12} />
              <span>{locale === "zh" ? "限额重置倒计时:" : "Limit Reset in:"} <strong className="text-ink font-mono">{stats.reset_countdown || "—"}</strong></span>
            </div>
            <div>
              <span>{locale === "zh" ? "更新于:" : "Updated:"} <strong className="text-ink font-mono">{stats.update_time}</strong></span>
            </div>
          </div>
        </div>
      ) : (
        <div className="p-4 text-center text-xs text-ink-light border border-dashed border-ink/20">
          {locale === "zh" ? "正在连接容器数据库读取最新额度..." : "Connecting to containers..."}
        </div>
      )}

      {/* 用户消费榜与模型排行预览 */}
      {stats?.users && stats.users.length > 0 ? (
        <div className="space-y-2">
          <div className="text-xs font-semibold text-ink flex items-center gap-1.5">
            <Users size={13} />
            <span>{locale === "zh" ? "当前活跃用户消费账单" : "User Quotas & Billing"}</span>
          </div>
          <div className="grid grid-cols-2 gap-2 text-xs">
            {stats.users.slice(0, 4).map((u: any, idx: number) => (
              <div key={idx} className="p-2 rounded-sm border border-ink/15 bg-paper-light flex items-center justify-between">
                <div>
                  <span className="font-bold text-ink">{u.name || u.label || "User"}</span>
                  <div className="text-[10px] text-ink-light font-mono">{u.tokens_str} ({u.requests} reqs)</div>
                </div>
                <div className="text-xs font-bold text-ink font-mono">{u.cost_str}</div>
              </div>
            ))}
          </div>
        </div>
      ) : null}

      {/* 视图选项 */}
      <div>
        <label className="text-xs font-semibold text-ink block mb-1.5">
          {locale === "zh" ? "墨水屏看板呈现样式：" : "Display Layout Style:"}
        </label>
        <div className="grid grid-cols-3 gap-2">
          {[
            { id: "overview", label: locale === "zh" ? "综合总览" : "Overview", tip: locale === "zh" ? "Token、用户与模型三合一" : "All-in-one summary" },
            { id: "users", label: locale === "zh" ? "用户消费榜" : "User Focus", tip: locale === "zh" ? "重点突出用户账单" : "Highlight users" },
            { id: "models", label: locale === "zh" ? "模型排行" : "Model Focus", tip: locale === "zh" ? "重点突出模型消耗" : "Highlight models" },
          ].map((item) => (
            <button
              key={item.id}
              type="button"
              onClick={() => setView(item.id)}
              className={`p-2 rounded-sm border text-left transition-all ${
                view === item.id
                  ? "border-ink bg-paper-dark/80 text-ink shadow-2xs"
                  : "border-ink/15 bg-white text-ink-light hover:border-ink/40"
              }`}
            >
              <div className="text-xs font-bold text-ink">{item.label}</div>
              <div className="text-[10px] text-ink-light mt-0.5 line-clamp-1">{item.tip}</div>
            </button>
          ))}
        </div>
      </div>

      {/* 底部按钮 */}
      <div className="pt-3 flex items-center justify-end gap-2 border-t border-ink/10">
        <Button variant="outline" size="sm" onClick={onClose}>
          {locale === "zh" ? "取消" : "Cancel"}
        </Button>
        <Button
          size="sm"
          disabled={previewLoading}
          onClick={async () => {
            onClose();
            await onSubmit({
              view,
            });
          }}
        >
          {locale === "zh" ? "应用并保存" : "Apply & Save"}
        </Button>
      </div>
    </div>
  );
}
