"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Gauge, CheckCircle2, XCircle, Key, Activity, Clock, ShieldCheck } from "lucide-react";

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
          ? "聚合本地 CLIProxyAPI 与 CPA-Usage-Keeper 容器，监控运行中的本地认证凭证：左侧呈现 5小时/7天 窗口重置时间与已用量，右侧环形仪表显示实时剩余配额！"
          : "Full integration with local CLIProxyAPI and CPA-Usage-Keeper containers. Displays active local auth files with 5h/7d reset countdowns, used volumes, and radial quota gauges."}
      </div>

      {/* 容器探针健康状态 */}
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

      {/* 核心指标统计 */}
      {stats ? (
        <div className="p-3 rounded-sm border border-ink/20 bg-white space-y-2">
          <div className="grid grid-cols-3 gap-2 text-center">
            <div>
              <div className="text-[10px] text-ink-light">{locale === "zh" ? "运行中认证文件" : "Active Auths"}</div>
              <div className="text-sm font-bold text-ink font-mono mt-0.5">
                {stats.auth_identities ? stats.auth_identities.length : 0} 个
              </div>
            </div>
            <div>
              <div className="text-[10px] text-ink-light">{locale === "zh" ? "5h 窗口重置" : "5h Reset"}</div>
              <div className="text-sm font-bold text-ink font-mono mt-0.5 text-amber-700">
                {stats.global_reset_5h || stats.reset_countdown || "持续可用"}
              </div>
            </div>
            <div>
              <div className="text-[10px] text-ink-light">{locale === "zh" ? "7天 窗口重置" : "7d Reset"}</div>
              <div className="text-sm font-bold text-ink font-mono mt-0.5">
                {stats.global_reset_7d || "持续可用"}
              </div>
            </div>
          </div>
        </div>
      ) : (
        <div className="p-4 text-center text-xs text-ink-light border border-dashed border-ink/20">
          {locale === "zh" ? "正在连接容器读取认证文件状态..." : "Connecting to containers..."}
        </div>
      )}

      {/* 运行中的本地认证文件明细（排除第三方APIKey） */}
      {stats?.auth_identities && stats.auth_identities.length > 0 ? (
        <div className="space-y-2">
          <div className="text-xs font-semibold text-ink flex items-center justify-between">
            <div className="flex items-center gap-1.5">
              <ShieldCheck size={13} className="text-emerald-700" />
              <span>{locale === "zh" ? "运行中的本地认证文件状态" : "Active Local Auth Files"}</span>
            </div>
            <span className="text-[10px] text-ink-light">
              {locale === "zh" ? "双重置窗口与配额监控" : "Dual reset windows & quota"}
            </span>
          </div>

          <div className="space-y-2">
            {stats.auth_identities.map((item: any, idx: number) => (
              <div
                key={idx}
                className="p-3 rounded-sm border border-ink/20 bg-paper-light flex items-center justify-between"
              >
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-sm text-ink">{item.display_name}</span>
                    <span className="text-[10px] px-1.5 py-0.2 bg-paper-dark border border-ink/20 rounded-xs font-mono font-bold text-ink">
                      {item.provider}
                    </span>
                    <span className="text-[10px] text-emerald-800 bg-emerald-100/90 px-1.5 py-0.2 rounded-xs font-semibold">
                      {locale === "zh" ? "正常调用中" : "Active"}
                    </span>
                  </div>

                  <div className="text-xs text-ink font-medium">
                    <span>5h重置: <strong className="font-mono text-amber-700">{item.reset_5h_str}</strong></span>
                    <span className="mx-2 text-ink/30">|</span>
                    <span>7天重置: <strong className="font-mono">{item.reset_7d_str}</strong></span>
                  </div>

                  <div className="text-[11px] text-ink-light font-mono">
                    {locale === "zh" ? "已用: " : "Used: "}
                    <strong className="text-ink">{item.tokens_str} Tokens</strong> · {item.requests} 次请求
                  </div>
                </div>

                {/* 环形进度模拟 (＜20%红色，<=60%黄色，其余黑色) */}
                <div className="flex flex-col items-center justify-center pl-3 border-l border-ink/10">
                  <div
                    className={`w-12 h-12 rounded-full border-3 flex items-center justify-center shadow-2xs ${
                      (item.remaining_pct_num ?? 100) < 20
                        ? "border-red-500 bg-red-50 text-red-600"
                        : (item.remaining_pct_num ?? 100) <= 60
                        ? "border-amber-500 bg-amber-50 text-amber-600"
                        : "border-ink bg-white text-ink"
                    }`}
                  >
                    <span className="text-xs font-bold font-mono">{item.remaining_pct}</span>
                  </div>
                  <span
                    className={`text-[9px] mt-1 font-medium ${
                      (item.remaining_pct_num ?? 100) < 20
                        ? "text-red-500"
                        : (item.remaining_pct_num ?? 100) <= 60
                        ? "text-amber-600"
                        : "text-ink-light"
                    }`}
                  >
                    {item.remaining_pct_num === 100
                      ? (locale === "zh" ? "配额充沛" : "Full")
                      : item.remaining_pct_num < 20
                      ? (locale === "zh" ? "配额告急" : "Critical")
                      : (locale === "zh" ? "剩余容量" : "Remaining")}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : null}

      {/* 看板呈现模式选择 */}
      <div>
        <label className="text-xs font-semibold text-ink block mb-1.5">
          {locale === "zh" ? "墨水屏呈现看板模式：" : "E-ink Display View Mode:"}
        </label>
        <div className="grid grid-cols-2 gap-2">
          {[
            {
              id: "auths",
              label: locale === "zh" ? "认证文件与限额 (推荐)" : "Auth Files & Quotas",
              tip: locale === "zh" ? "双重置时间 + 右侧环形进度条" : "5h/7d reset & radial gauge",
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
          {locale === "zh" ? "保存并切换看板" : "Save & Switch View"}
        </Button>
      </div>
    </div>
  );
}
