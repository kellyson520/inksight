"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Gauge, CheckCircle2, XCircle, Key, Activity, Clock, Layers, Sparkles } from "lucide-react";

interface CpaQuotaConfigProps {
  initialView?: string;
  locale: string;
  previewLoading: boolean;
  onClose: () => void;
  onSubmit: (override: Record<string, unknown>) => Promise<void>;
}

export function CpaQuotaConfig({
  initialView = "auths",
  locale,
  previewLoading,
  onClose,
  onSubmit,
}: CpaQuotaConfigProps) {
  const [view, setView] = useState(initialView || "auths");
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
          ? "深度纳入本地 CLIProxyAPI 与 CPA-Usage-Keeper 容器，在墨水屏与后台清晰掌握本地认证文件（Auth Files）的重置倒计时、已使用量、剩余限额百分比以及下游消费！"
          : "Full integration with local CLIProxyAPI and CPA-Usage-Keeper containers. Monitor local auth files reset countdowns, used volumes, remaining quotas, and downstream billing."}
      </div>

      {/* 容器探针健康指示 */}
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

      {/* 核心指标概览 */}
      {stats ? (
        <div className="p-3 rounded-sm border border-ink/20 bg-white space-y-2">
          <div className="grid grid-cols-3 gap-2 text-center">
            <div>
              <div className="text-[10px] text-ink-light">{locale === "zh" ? "认证文件数" : "Auth Files"}</div>
              <div className="text-sm font-bold text-ink font-mono mt-0.5">
                {stats.auth_identities ? stats.auth_identities.length : 0} 个
              </div>
            </div>
            <div>
              <div className="text-[10px] text-ink-light">{locale === "zh" ? "窗口重置倒计时" : "Reset Countdown"}</div>
              <div className="text-sm font-bold text-ink font-mono mt-0.5 text-amber-700">
                {stats.reset_countdown || "持续可用"}
              </div>
            </div>
            <div>
              <div className="text-[10px] text-ink-light">{locale === "zh" ? "今日 Token 消耗" : "Today Tokens"}</div>
              <div className="text-sm font-bold text-ink font-mono mt-0.5">{stats.today_tokens_str || "0"}</div>
            </div>
          </div>
        </div>
      ) : (
        <div className="p-4 text-center text-xs text-ink-light border border-dashed border-ink/20">
          {locale === "zh" ? "正在连接容器数据库读取最新认证文件与额度..." : "Connecting to containers..."}
        </div>
      )}

      {/* 本地认证文件请求活动与限额状态 */}
      {stats?.auth_identities && stats.auth_identities.length > 0 ? (
        <div className="space-y-2">
          <div className="text-xs font-semibold text-ink flex items-center justify-between">
            <div className="flex items-center gap-1.5">
              <Key size={13} />
              <span>{locale === "zh" ? "本地认证文件请求活动及限额" : "Auth Files Quota & Usage"}</span>
            </div>
            <span className="text-[10px] text-ink-light">
              {locale === "zh" ? "含重置倒计时与已用量" : "Reset times & used volumes"}
            </span>
          </div>

          <div className="space-y-1.5 max-h-48 overflow-y-auto pr-1">
            {stats.auth_identities.map((item: any, idx: number) => (
              <div
                key={idx}
                className="p-2 rounded-sm border border-ink/15 bg-paper-light flex items-center justify-between text-xs"
              >
                <div className="space-y-0.5">
                  <div className="flex items-center gap-1.5">
                    <span className="font-bold text-ink">{item.display_name || item.name}</span>
                    <span className="text-[9px] px-1 py-0.2 bg-paper-dark border border-ink/20 rounded-xs font-mono font-bold text-ink/80">
                      {item.provider}
                    </span>
                    {item.disabled && (
                      <span className="text-[9px] px-1 py-0.2 bg-red-100 text-red-700 rounded-xs">
                        {locale === "zh" ? "已禁用" : "Disabled"}
                      </span>
                    )}
                  </div>
                  <div className="text-[10px] text-ink-light font-mono">
                    {locale === "zh" ? "已使用: " : "Used: "}
                    <strong className="text-ink">{item.tokens_str}</strong> ({item.requests} reqs) ·{" "}
                    {locale === "zh" ? "剩余: " : "Rem: "}
                    <span className="text-emerald-700 font-semibold">{item.remaining_pct}</span>
                  </div>
                </div>

                <div className="text-right">
                  <div className="text-[10px] text-ink-light">{locale === "zh" ? "限额重置" : "Reset"}</div>
                  <div className="text-xs font-bold text-ink font-mono mt-0.5 flex items-center gap-1 justify-end">
                    <Clock size={11} className="text-amber-600" />
                    <span>{item.reset_str}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : null}

      {/* 看板呈现模式切换 */}
      <div>
        <label className="text-xs font-semibold text-ink block mb-1.5">
          {locale === "zh" ? "墨水屏呈现看板模式：" : "E-ink Display View Mode:"}
        </label>
        <div className="grid grid-cols-2 gap-2">
          {[
            {
              id: "auths",
              label: locale === "zh" ? "认证文件与限额" : "Auth Files & Quotas",
              tip: locale === "zh" ? "不同认证文件重置时间与已用量" : "Auth reset countdown & volume",
            },
            {
              id: "overview",
              label: locale === "zh" ? "综合总览看板" : "Comprehensive",
              tip: locale === "zh" ? "认证文件+账单+模型综合展示" : "Auths, billing and models",
            },
            {
              id: "users",
              label: locale === "zh" ? "用户消费账单" : "User Billing",
              tip: locale === "zh" ? "API Key 用户消费排行榜" : "API keys spending ranking",
            },
            {
              id: "models",
              label: locale === "zh" ? "模型消耗分布" : "Model Usage",
              tip: locale === "zh" ? "热门 AI 模型吞吐与调用量" : "Token volume per model",
            },
          ].map((item) => (
            <button
              key={item.id}
              type="button"
              onClick={() => setView(item.id)}
              className={`p-2.5 rounded-sm border text-left transition-all ${
                view === item.id
                  ? "border-ink bg-paper-dark text-ink shadow-2xs"
                  : "border-ink/15 bg-white text-ink-light hover:border-ink/40"
              }`}
            >
              <div className="text-xs font-bold text-ink">{item.label}</div>
              <div className="text-[10px] text-ink-light mt-0.5 line-clamp-1">{item.tip}</div>
            </button>
          ))}
        </div>
      </div>

      {/* 底部确认按钮 */}
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
          {locale === "zh" ? "保存并切换看板" : "Save & Switch View"}
        </Button>
      </div>
    </div>
  );
}
