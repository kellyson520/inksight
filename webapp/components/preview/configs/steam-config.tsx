"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Gamepad2, RotateCcw, Check, ExternalLink } from "lucide-react";

interface SteamConfigProps {
  initialSteamUrl?: string;
  locale: string;
  previewLoading: boolean;
  onClose: () => void;
  onSubmit: (override: Record<string, unknown>) => Promise<void>;
}

const DEFAULT_TEST_URL = "https://steamcommunity.com/profiles/76561198978201763/";

export function SteamConfig({
  initialSteamUrl = "",
  locale,
  previewLoading,
  onClose,
  onSubmit,
}: SteamConfigProps) {
  const isZh = locale !== "en";
  const [steamUrl, setSteamUrl] = useState(initialSteamUrl || "");

  const handleSubmit = async () => {
    await onSubmit({ steam_url: steamUrl.trim() });
    onClose();
  };

  return (
    <div className="space-y-5">
      <div className="space-y-2">
        <label className="text-xs font-semibold text-ink-muted uppercase tracking-wider block">
          {isZh ? "Steam 个人主页链接" : "Steam Community Profile URL"}
        </label>
        <input
          type="url"
          value={steamUrl}
          onChange={(e) => setSteamUrl(e.target.value)}
          placeholder={DEFAULT_TEST_URL}
          className="w-full rounded-sm border border-ink/20 px-3 py-2 text-sm bg-white font-mono"
        />
        <div className="flex items-center justify-between text-xs text-ink-light pt-1">
          <span>{isZh ? "留空将自动使用用户个人中心配置的主页" : "Leave blank to use profile settings"}</span>
          <button
            type="button"
            onClick={() => setSteamUrl(DEFAULT_TEST_URL)}
            className="flex items-center gap-1 text-ink underline hover:text-ink/80"
          >
            <RotateCcw size={12} />
            {isZh ? "填入官方测试链接" : "Use Test URL"}
          </button>
        </div>
      </div>

      <div className="p-3 rounded-lg border border-border bg-muted/20 text-xs text-ink-light space-y-1">
        <div className="font-semibold text-ink flex items-center gap-1.5">
          <Gamepad2 size={14} />
          {isZh ? "数据公开提示" : "Privacy Notice"}
        </div>
        <p>
          {isZh
            ? "请确保对应 Steam 账号的「个人资料」与「游戏详情」权限设置为【公开】，否则成就与时长将无法展示。"
            : "Ensure your Steam Profile and Game Details privacy settings are set to 'Public' so achievements and stats can be retrieved."}
        </p>
      </div>

      <div className="pt-3 flex items-center justify-end gap-2 border-t border-ink/10">
        <Button variant="outline" size="sm" onClick={onClose} disabled={previewLoading}>
          {isZh ? "取消" : "Cancel"}
        </Button>
        <Button size="sm" onClick={handleSubmit} disabled={previewLoading}>
          {isZh ? "保存并预览" : "Save & Preview"}
        </Button>
      </div>
    </div>
  );
}
