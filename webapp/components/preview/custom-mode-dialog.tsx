"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Loader2 } from "lucide-react";

interface CustomModeDialogProps {
  isOpen: boolean;
  locale: string;
  onClose: () => void;
  onGenerated: (modeDef: unknown) => Promise<void>;
  showToast: (msg: string, type: "success" | "error" | "info") => void;
}

export function CustomModeDialog({
  isOpen,
  locale,
  onClose,
  onGenerated,
  showToast,
}: CustomModeDialogProps) {
  const [customDesc, setCustomDesc] = useState("");
  const [customGenerating, setCustomGenerating] = useState(false);

  if (!isOpen) return null;

  const handleGenerate = async () => {
    if (!customDesc.trim()) {
      showToast(locale === "zh" ? "请输入模式描述" : "Please enter a description", "error");
      return;
    }

    setCustomGenerating(true);
    try {
      const res = await fetch("/api/modes/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ description: customDesc.trim() }),
      });
      const data = await res.json();
      if (!data.ok) throw new Error(data.error || "Generate failed");
      onClose();
      await onGenerated(data.mode_def);
    } catch (e) {
      showToast(
        (locale === "zh" ? "生成失败: " : "Generate failed: ") +
          (e instanceof Error ? e.message : "Unknown error"),
        "error",
      );
    } finally {
      setCustomGenerating(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/60 dark:bg-black/80 backdrop-blur-xs" onClick={onClose} />
      <div className="relative w-full max-w-lg rounded-sm border border-ink/20 dark:border-zinc-800 bg-white dark:bg-zinc-900 text-ink dark:text-zinc-100 p-5 shadow-2xl space-y-4">
        <div className="flex items-center justify-between border-b border-ink/10 pb-3">
          <h3 className="text-sm font-bold text-ink">
            {locale === "zh" ? "AI 智能生成自定义墨水屏模式" : "Generate Custom Mode with AI"}
          </h3>
          <button className="text-ink-light hover:text-ink text-sm" onClick={onClose}>
            ✕
          </button>
        </div>

        <div className="space-y-2">
          <label className="text-xs font-semibold text-ink block">
            {locale === "zh" ? "描述你想要的墨水屏排版与功能：" : "Describe desired layout & content:"}
          </label>
          <textarea
            value={customDesc}
            onChange={(e) => setCustomDesc(e.target.value)}
            placeholder={
              locale === "zh"
                ? "例如：一个展示三行每日复盘清单、一个大号完成度进度条，带古典双线边框的极简卡片..."
                : "e.g. A minimalist reflection dashboard with progress bar..."
            }
            rows={4}
            className="w-full rounded-sm border border-ink/20 dark:border-zinc-700 p-2.5 text-xs bg-white dark:bg-zinc-950 text-ink dark:text-zinc-100"
          />
        </div>

        <div className="flex items-center justify-end gap-2 pt-2">
          <Button variant="outline" size="sm" onClick={onClose}>
            {locale === "zh" ? "取消" : "Cancel"}
          </Button>
          <Button
            size="sm"
            onClick={handleGenerate}
            disabled={customGenerating || !customDesc.trim()}
            className="bg-ink text-white"
          >
            {customGenerating ? (
              <>
                <Loader2 size={13} className="animate-spin mr-1.5" />
                <span>{locale === "zh" ? "生成中..." : "Generating..."}</span>
              </>
            ) : (
              <span>{locale === "zh" ? "开始生成并预览" : "Generate & Preview"}</span>
            )}
          </Button>
        </div>
      </div>
    </div>
  );
}
