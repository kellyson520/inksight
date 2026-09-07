"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Activity, ShieldCheck, Link2, Server } from "lucide-react";

interface MihomoSubConfigProps {
  initialSubscriptionUrl?: string;
  initialApiUrl?: string;
  initialApiSecret?: string;
  initialName?: string;
  locale: string;
  previewLoading: boolean;
  onClose: () => void;
  onSubmit: (override: Record<string, unknown>) => Promise<void>;
}

export function MihomoSubConfig({
  initialSubscriptionUrl = "",
  initialApiUrl = "http://mihomo-cliproxy:9090",
  initialApiSecret = "",
  initialName = "",
  locale,
  previewLoading,
  onClose,
  onSubmit,
}: MihomoSubConfigProps) {
  const isEn = locale === "en";
  const [subUrl, setSubUrl] = useState(initialSubscriptionUrl);
  const [apiUrl, setApiUrl] = useState(initialApiUrl);
  const [apiSecret, setApiSecret] = useState(initialApiSecret);
  const [name, setName] = useState(initialName);

  const handleSubmit = async () => {
    await onSubmit({
      subscription_url: subUrl.trim(),
      api_url: apiUrl.trim(),
      api_secret: apiSecret.trim(),
      name: name.trim(),
    });
  };

  return (
    <div className="space-y-4 text-xs">
      <div className="rounded-lg border border-border/70 bg-muted/40 p-3.5 space-y-2">
        <div className="flex items-center gap-2 font-medium text-foreground">
          <Activity className="h-4 w-4 text-emerald-500" />
          <span>{isEn ? "Mihomo (Clash.Meta) Container & Subscription" : "Mihomo (Clash.Meta) 容器与订阅监控"}</span>
        </div>
        <p className="text-muted-foreground leading-relaxed text-[11px]">
          {isEn
            ? "Monitors Mihomo container connectivity, proxy subscription quota usage, total bandwidth, and expiration date directly on your e-ink screen."
            : "为墨水屏提供 Mihomo 容器状态监控与代理订阅流量额度、有效期、剩余天数、节点状态看板。默认自动探测本地运行的容器。"}
        </p>
      </div>

      <div className="space-y-3">
        <div>
          <label className="text-[11px] font-medium text-muted-foreground mb-1 flex items-center gap-1.5">
            <Link2 className="h-3.5 w-3.5 text-blue-500" />
            {isEn ? "Subscription Link (Optional)" : "代理订阅链接 (可选)"}
          </label>
          <input
            type="text"
            className="w-full rounded-md border border-input bg-background px-3 py-1.5 text-xs focus:outline-none focus:ring-1 focus:ring-ring"
            placeholder={isEn ? "https://sub.domain.com/api/v1/client/subscribe?token=..." : "机场订阅链接 (支持 Subscription-Userinfo 响应头)"}
            value={subUrl}
            onChange={(e) => setSubUrl(e.target.value)}
          />
          <p className="text-[10px] text-muted-foreground mt-1">
            {isEn ? "Directly fetches quota from the subscription provider header." : "若填写订阅链接，优先从服务商响应头解析流量与到期时间。"}
          </p>
        </div>

        <div>
          <label className="text-[11px] font-medium text-muted-foreground mb-1 flex items-center gap-1.5">
            <Server className="h-3.5 w-3.5 text-indigo-500" />
            {isEn ? "Mihomo Controller API URL" : "Mihomo 外部控制 API 地址"}
          </label>
          <input
            type="text"
            className="w-full rounded-md border border-input bg-background px-3 py-1.5 text-xs focus:outline-none focus:ring-1 focus:ring-ring font-mono"
            placeholder="http://mihomo-cliproxy:9090 或 http://127.0.0.1:9090"
            value={apiUrl}
            onChange={(e) => setApiUrl(e.target.value)}
          />
        </div>

        <div>
          <label className="text-[11px] font-medium text-muted-foreground mb-1 flex items-center gap-1.5">
            <ShieldCheck className="h-3.5 w-3.5 text-amber-500" />
            {isEn ? "Mihomo Secret (Optional)" : "Mihomo API Secret (可选)"}
          </label>
          <input
            type="password"
            className="w-full rounded-md border border-input bg-background px-3 py-1.5 text-xs focus:outline-none focus:ring-1 focus:ring-ring font-mono"
            placeholder={isEn ? "Leave empty for auto-detection" : "留空则自动从服务器挂载文件探测"}
            value={apiSecret}
            onChange={(e) => setApiSecret(e.target.value)}
          />
        </div>

        <div>
          <label className="text-[11px] font-medium text-muted-foreground mb-1">
            {isEn ? "Display Name (Optional)" : "订阅服务商备注名称 (可选)"}
          </label>
          <input
            type="text"
            className="w-full rounded-md border border-input bg-background px-3 py-1.5 text-xs focus:outline-none focus:ring-1 focus:ring-ring"
            placeholder={isEn ? "e.g. My Airport / Mihomo Proxy" : "如 我的主力机场 / Mihomo 节点"}
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
        </div>
      </div>

      <div className="flex justify-end gap-2 pt-2">
        <Button variant="outline" size="sm" onClick={onClose} disabled={previewLoading}>
          {isEn ? "Cancel" : "取消"}
        </Button>
        <Button size="sm" onClick={handleSubmit} disabled={previewLoading}>
          {previewLoading ? (isEn ? "Updating..." : "生成中...") : isEn ? "Save & Preview" : "保存并生成预览"}
        </Button>
      </div>
    </div>
  );
}
