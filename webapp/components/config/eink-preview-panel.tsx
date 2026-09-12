"use client";

import Image from "next/image";
import type { ReactNode } from "react";
import { Eye, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export function EInkPreviewPanel({
  tr,
  previewModeLabel,
  previewLoading,
  previewStatusText,
  previewImg,
  previewCacheHit,
  previewLlmStatus,
  canApplyToScreen,
  applyToScreenLoading,
  onRegenerate,
  onApplyToScreen,
  rightActions,
  screenW = 400,
  screenH = 300,
}: {
  tr: (zh: string, en: string) => string;
  previewModeLabel: string;
  previewLoading: boolean;
  previewStatusText: string;
  previewImg: string | null;
  previewCacheHit: boolean | null;
  previewLlmStatus: string | null;
  canApplyToScreen: boolean;
  applyToScreenLoading: boolean;
  onRegenerate: () => void;
  onApplyToScreen: () => void;
  rightActions?: ReactNode;
  screenW?: number;
  screenH?: number;
}) {
  return (
    <Card className="w-full min-w-0 max-w-full border-ink/15 shadow-xs overflow-hidden">
      <CardHeader className="p-3.5 pb-2 border-b border-ink/10">
        <CardTitle className="flex items-center justify-between gap-2 flex-wrap">
          <span className="text-sm font-bold text-ink">{tr("墨水屏预览", "E-Ink Preview")}</span>
          <span className="text-xs font-semibold px-2 py-0.5 rounded bg-ink/5 text-ink truncate max-w-[180px]" title={previewModeLabel}>
            {previewModeLabel}
          </span>
        </CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col p-0 w-full min-w-0">
        <div className="border-b border-ink/10 bg-paper p-3 flex flex-col items-center justify-center w-full min-h-[200px]">
          {previewLoading ? (
            <div className="flex items-center justify-center w-full py-8">
              <div className="text-center">
                <Loader2 size={28} className="animate-spin mx-auto text-ink-light mb-2" />
                <p className="text-xs text-ink-light">{previewStatusText || tr("预览生成中...", "Generating preview...")}</p>
              </div>
            </div>
          ) : previewImg ? (
            <div className="flex flex-col items-center gap-2 w-full">
              <div
                className="relative w-full max-w-full bg-white border border-ink/20 rounded-sm overflow-hidden shadow-2xs"
                style={{ aspectRatio: `${screenW} / ${screenH}`, maxHeight: "380px" }}
              >
                <Image src={previewImg} alt="Preview" fill unoptimized className="object-contain" />
              </div>
              {previewLlmStatus ? (
                <p className="text-[10px] text-ink-light text-center px-2 truncate w-full">{previewLlmStatus}</p>
              ) : null}
            </div>
          ) : (
            <div className="flex items-center justify-center w-full py-8">
              <div className="text-center">
                <Eye size={28} className="mx-auto text-ink-light mb-2 opacity-50" />
                <p className="text-xs text-ink-light">{tr("点击模式卡片上的「预览」查看效果", "Click Preview on any mode to view output")}</p>
              </div>
            </div>
          )}
        </div>

        <div className="p-3 bg-white dark:bg-zinc-900 flex flex-col gap-2 w-full">
          {previewImg && !previewLoading && previewCacheHit === true ? (
            <div className="text-[11px] text-amber-800 dark:text-amber-300 bg-amber-50 dark:bg-amber-950/50 border border-amber-200 dark:border-amber-800 rounded-sm px-2 py-1 leading-tight">
              {tr(
                "当前预览为缓存内容。点击重新生成可刷新。",
                'Cached preview. Click regenerate to update.',
              )}
            </div>
          ) : null}
          <div className="flex gap-2 items-center flex-wrap">
            <Button
              variant="outline"
              size="sm"
              onClick={onRegenerate}
              disabled={!previewModeLabel || previewLoading}
              className="text-xs h-8 px-2.5 bg-white text-ink border-ink/20 hover:bg-ink hover:text-white"
            >
              {tr("重新生成", "Regenerate")}
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={onApplyToScreen}
              disabled={!canApplyToScreen || applyToScreenLoading || previewLoading}
              className="text-xs h-8 px-2.5 bg-white text-ink border-ink/20 hover:bg-ink hover:text-white"
            >
              {applyToScreenLoading ? <Loader2 size={13} className="animate-spin mr-1" /> : null}
              {tr("应用上屏", "Apply")}
            </Button>
            {rightActions ? <div className="ml-auto flex items-center gap-1.5 flex-wrap">{rightActions}</div> : null}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

