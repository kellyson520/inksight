"use client";

import Image from "next/image";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ColorSelect } from "@/components/ui/color-select";
import { ScreenSizeSelect } from "@/components/ui/screen-size-select";
import { RefreshCw, Sliders, Loader2, Eye, Download } from "lucide-react";
import { CONFIGURABLE_MODES } from "./types";

interface PreviewCanvasProps {
  previewMode: string;
  previewModeName: string;
  previewWidth: number;
  previewHeight: number;
  previewColors: number;
  previewImageUrl: string | null;
  previewLoading: boolean;
  previewLlmStatus: string | null;
  locale: string;
  onColorChange: (colors: number) => void;
  onSizeChange: (width: number, height: number) => void;
  onRefresh: () => void;
  onOpenConfig: (modeId: string) => void;
}

export function PreviewCanvas({
  previewMode,
  previewModeName,
  previewWidth,
  previewHeight,
  previewColors,
  previewImageUrl,
  previewLoading,
  previewLlmStatus,
  locale,
  onColorChange,
  onSizeChange,
  onRefresh,
  onOpenConfig,
}: PreviewCanvasProps) {
  const isConfigurable = Boolean(CONFIGURABLE_MODES[previewMode]);

  return (
    <Card className="border-ink/20 dark:border-zinc-800 shadow-md bg-white dark:bg-zinc-900">
      <CardHeader className="pb-3 border-b border-ink/10">
        <div className="flex items-center justify-between gap-2 flex-wrap">
          <div>
            <span className="text-sm font-bold text-ink flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
              {locale === "zh" ? "墨水屏实时预览" : "E-Ink Live Preview"}
            </span>
          </div>

          {/* 屏幕尺寸与颜色模式快速切换 */}
          <div className="flex items-center gap-2">
            <ColorSelect
              value={previewColors}
              onChange={onColorChange}
              tr={(zh, en) => (locale === "zh" ? zh : en)}
            />
            <ScreenSizeSelect
              width={previewWidth}
              height={previewHeight}
              onChange={onSizeChange}
              tr={(zh, en) => (locale === "zh" ? zh : en)}
            />
            <Button
              variant="outline"
              size="sm"
              onClick={onRefresh}
              disabled={previewLoading}
              className="h-8 px-2 text-xs"
              title={locale === "zh" ? "重新渲染刷新" : "Refresh"}
            >
              <RefreshCw size={13} className={previewLoading ? "animate-spin" : ""} />
            </Button>
          </div>
        </div>

        {/* 当前激活模式信息横条 */}
        <div className="mt-2.5 flex items-center justify-between gap-2 pt-2 border-t border-ink/5">
          <div className="flex items-center gap-2 truncate">
            <span className="text-xs font-bold text-ink truncate">
              {previewModeName}
            </span>
            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-ink/5 text-ink-light">
              {previewMode}
            </span>
          </div>

          {/* 若当前模式支持调节，提供常驻配置入口 */}
          {isConfigurable ? (
            <button
              onClick={() => onOpenConfig(previewMode)}
              className="text-xs font-medium text-ink bg-paper-dark hover:bg-ink hover:text-white px-2.5 py-1 rounded-sm border border-ink/15 flex items-center gap-1 transition-colors shrink-0"
            >
              <Sliders size={12} />
              <span>{locale === "zh" ? "参数调节" : "Settings"}</span>
            </button>
          ) : null}
        </div>
      </CardHeader>

      <CardContent className="p-4 flex flex-col items-center">
        {/* 墨水屏设备仿真画框 (带边框与阴影) */}
        <div
          className="relative w-full rounded-sm border-2 border-ink/80 dark:border-zinc-700 bg-paper-light dark:bg-zinc-950 p-2 shadow-inner flex flex-col items-center justify-center overflow-hidden"
          style={{ aspectRatio: `${previewWidth} / ${previewHeight}` }}
        >
          {previewLoading ? (
            <div className="absolute inset-0 z-10 bg-white/80 dark:bg-zinc-950/80 backdrop-blur-2xs flex flex-col items-center justify-center">
              <Loader2 size={32} className="animate-spin text-ink dark:text-zinc-100 mb-2" />
              <p className="text-xs font-medium text-ink dark:text-zinc-100">
                {locale === "zh" ? "渲染生成中..." : "Generating preview..."}
              </p>
            </div>
          ) : null}

          {previewImageUrl ? (
            <div className="eink-paper relative w-full h-full bg-white flex items-center justify-center overflow-hidden rounded-xs">
              <Image
                src={previewImageUrl}
                alt="InkSight E-Ink Preview"
                fill
                className="object-contain"
                unoptimized
              />
            </div>
          ) : (
            <div className="text-center p-6">
              <Eye size={36} className="mx-auto text-ink-light mb-2 opacity-50" />
              <p className="text-xs text-ink-light">
                {locale === "zh" ? "点击左侧模式卡片立即呈现预览" : "Click any mode on the left to render"}
              </p>
            </div>
          )}
        </div>

        {/* 底部状态指示条 */}
        <div className="w-full mt-3 flex items-center justify-between text-[11px] text-ink-light px-1">
          <div className="truncate">
            {previewLlmStatus ? (
              <span className="text-ink font-medium">● {previewLlmStatus}</span>
            ) : (
              <span>● {previewWidth}×{previewHeight} · {previewColors >= 3 ? "3-Color BWR" : "1-Bit BW"}</span>
            )}
          </div>
          {previewImageUrl ? (
            <a
              href={previewImageUrl}
              download={`inksight-${previewMode.toLowerCase()}-${previewWidth}x${previewHeight}.png`}
              className="hover:text-ink flex items-center gap-1 transition-colors"
            >
              <Download size={12} />
              <span>{locale === "zh" ? "保存图像" : "Export"}</span>
            </a>
          ) : null}
        </div>
      </CardContent>
    </Card>
  );
}
