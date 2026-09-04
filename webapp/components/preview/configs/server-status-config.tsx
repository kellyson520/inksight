"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Server, Copy, Check, Terminal, Cpu, HardDrive } from "lucide-react";

interface ServerStatusConfigProps {
  locale: string;
  previewLoading: boolean;
  onClose: () => void;
  onSubmit: (override: Record<string, unknown>) => Promise<void>;
}

export function ServerStatusConfig({
  locale,
  previewLoading,
  onClose,
  onSubmit,
}: ServerStatusConfigProps) {
  const [serverName, setServerName] = useState("主生产服务器");
  const [serverKey, setServerKey] = useState("default");
  const [cpuPct, setCpuPct] = useState(38);
  const [memPct, setMemPct] = useState(65);
  const [diskPct, setDiskPct] = useState(48);
  const [liveMetrics, setLiveMetrics] = useState<Record<string, unknown> | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    fetch("/api/server-status")
      .then((res) => res.json())
      .then((d) => {
        if (d.success && d.metrics) {
          setLiveMetrics(d.metrics);
          if (d.metrics.server_name) setServerName(String(d.metrics.server_name));
          if (d.metrics.cpu_pct !== undefined) setCpuPct(Number(d.metrics.cpu_pct));
          if (d.metrics.mem_pct !== undefined) setMemPct(Number(d.metrics.mem_pct));
          if (d.metrics.disk_pct !== undefined) setDiskPct(Number(d.metrics.disk_pct));
        }
      })
      .catch(() => {});
  }, []);

  const curlCommand = `curl -sSL ${typeof window !== "undefined" ? window.location.origin : ""}/api/server-status/script?key=${encodeURIComponent(serverKey || "default")} | bash`;

  const handleCopyScript = () => {
    if (navigator.clipboard) {
      navigator.clipboard.writeText(curlCommand);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div className="space-y-4">
      <div className="text-xs text-ink-light leading-relaxed">
        {locale === "zh"
          ? "实时监控 Linux 主机、VPS 或宝塔面板的 CPU、内存、磁盘与系统负载！支持直接采集当前宿主机，或使用下方的一键脚本让远程服务器定期上报。"
          : "Monitor Linux servers, VPS, or BaoTa panel in real time (CPU, RAM, Disk, Load). Collects host stats or receives remote reports via a 1-line script."}
      </div>

      {/* 实时探针状态卡片 */}
      {liveMetrics ? (
        <div className="p-2.5 rounded-sm border border-ink/20 bg-paper-light space-y-1.5">
          <div className="flex items-center justify-between text-xs font-semibold text-ink">
            <div className="flex items-center gap-1.5">
              <Server size={14} className="text-ink" />
              <span>当前检测主机: {String(liveMetrics.server_name || "Linux-Host")}</span>
            </div>
            <span className="text-[10px] px-1.5 py-0.5 rounded-xs bg-green-100 text-green-800 font-normal">
              {String(liveMetrics.source === "local" ? (locale === "zh" ? "本地宿主机" : "Local Host") : (locale === "zh" ? "远程上报" : "Remote Reported"))}
            </span>
          </div>
          <div className="grid grid-cols-3 gap-2 text-[11px] text-ink-light pt-1">
            <div className="flex items-center gap-1">
              <Cpu size={12} />
              <span>CPU: <strong className="text-ink font-mono">{String(liveMetrics.cpu_pct)}%</strong></span>
            </div>
            <div className="flex items-center gap-1">
              <HardDrive size={12} />
              <span>内存: <strong className="text-ink font-mono">{String(liveMetrics.mem_pct)}%</strong></span>
            </div>
            <div>
              <span>负载: <strong className="text-ink font-mono">{String(liveMetrics.load_str || "-")}</strong></span>
            </div>
          </div>
        </div>
      ) : null}

      {/* 手动微调与模拟表单 */}
      <div className="space-y-3">
        <div className="grid grid-cols-2 gap-2">
          <div>
            <label className="text-xs font-semibold text-ink block mb-1">
              {locale === "zh" ? "服务器名称：" : "Server Name:"}
            </label>
            <input
              value={serverName}
              onChange={(e) => setServerName(e.target.value)}
              className="w-full rounded-sm border border-ink/20 px-2.5 py-1 text-xs bg-white font-medium"
              placeholder="如 阿里云-主服"
            />
          </div>
          <div>
            <label className="text-xs font-semibold text-ink block mb-1">
              {locale === "zh" ? "匹配标识 Key：" : "Server Key:"}
            </label>
            <input
              value={serverKey}
              onChange={(e) => setServerKey(e.target.value)}
              className="w-full rounded-sm border border-ink/20 px-2.5 py-1 text-xs bg-white font-mono"
              placeholder="default"
            />
          </div>
        </div>

        <div className="grid grid-cols-3 gap-2">
          <div>
            <label className="text-xs text-ink block mb-1">CPU (%)</label>
            <input
              type="number"
              min={0}
              max={100}
              value={cpuPct}
              onChange={(e) => setCpuPct(Number(e.target.value))}
              className="w-full rounded-sm border border-ink/20 px-2 py-1 text-xs"
            />
          </div>
          <div>
            <label className="text-xs text-ink block mb-1">内存 (%)</label>
            <input
              type="number"
              min={0}
              max={100}
              value={memPct}
              onChange={(e) => setMemPct(Number(e.target.value))}
              className="w-full rounded-sm border border-ink/20 px-2 py-1 text-xs"
            />
          </div>
          <div>
            <label className="text-xs text-ink block mb-1">磁盘 (%)</label>
            <input
              type="number"
              min={0}
              max={100}
              value={diskPct}
              onChange={(e) => setDiskPct(Number(e.target.value))}
              className="w-full rounded-sm border border-ink/20 px-2 py-1 text-xs"
            />
          </div>
        </div>
      </div>

      {/* 一键 Crontab / 宝塔面板上报脚本 */}
      <div className="pt-2">
        <div className="flex items-center justify-between mb-1">
          <div className="text-xs font-semibold text-ink flex items-center gap-1">
            <Terminal size={12} />
            <span>{locale === "zh" ? "宝塔面板 / Crontab 计划任务一键脚本：" : "1-Line Crontab / Shell Script:"}</span>
          </div>
          <button
            type="button"
            onClick={handleCopyScript}
            className="text-[11px] text-ink-light hover:text-ink flex items-center gap-1 underline"
          >
            {copied ? <Check size={12} className="text-green-600" /> : <Copy size={12} />}
            <span>{copied ? (locale === "zh" ? "已复制" : "Copied") : (locale === "zh" ? "复制命令" : "Copy")}</span>
          </button>
        </div>
        <pre className="p-2 rounded-sm bg-ink text-white/90 text-[11px] font-mono overflow-x-auto whitespace-pre-wrap break-all select-all">
          {curlCommand}
        </pre>
        <p className="text-[10px] text-ink-light mt-1">
          {locale === "zh"
            ? "在远程 VPS 或宝塔面板中添加定时任务（如每 2 分钟执行一次），即可实时同步。"
            : "Add this to your remote Linux cron (e.g. */2 * * * *) to automatically report stats."}
        </p>
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
              server_name: serverName,
              server_key: serverKey,
              cpu_pct: cpuPct,
              mem_pct: memPct,
              disk_pct: diskPct,
            });
          }}
        >
          {locale === "zh" ? "应用并预览" : "Apply & Preview"}
        </Button>
      </div>
    </div>
  );
}
