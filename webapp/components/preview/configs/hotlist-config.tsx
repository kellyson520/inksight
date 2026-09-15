"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { HOTLIST_AVAILABLE_PLATFORMS, HOTLIST_AVAILABLE_STYLES } from "../types";

interface HotlistConfigProps {
  modeId?: string;
  initialPlatforms: string[];
  initialStyle?: string;
  locale: string;
  previewLoading: boolean;
  onClose: () => void;
  onSubmit: (platforms: string[], style: string) => Promise<void>;
}

export function HotlistConfig({
  modeId,
  initialPlatforms,
  initialStyle = "dense_grid",
  locale,
  previewLoading,
  onClose,
  onSubmit,
}: HotlistConfigProps) {
  const isStandalone = Boolean(modeId && modeId !== "HOTLIST");
  const [platforms, setPlatforms] = useState<string[]>(
    initialPlatforms.length > 0 ? initialPlatforms : ["zhihu", "weibo", "bilibili"]
  );
  const [style, setStyle] = useState<string>(initialStyle);

  return (
    <div className="space-y-4">
      <div className="text-xs text-ink-light leading-relaxed">
        {isStandalone
          ? locale === "zh"
            ? "选择在墨水屏上的呈现样式。本模块专享实时热榜数据，排行榜完整展示前 8 项内容，并支持图文封面大卡展示！"
            : "Choose layout style. Displays top 8 trending items and supports illustrated cover card view."
          : locale === "zh"
          ? "支持网易云音乐、豆瓣电影、抖音、微信、知乎、微博、B站、36氪等主流平台，排行榜完整展示前 8 项内容，支持图文大卡展示！"
          : "Supports mainstream platforms (NetEase, Douban, Douyin, WeChat, Zhihu, etc.) and top 8 items with illustrated cover cards."}
      </div>

      {/* Style selector */}
      <div className="space-y-2">
        <label className="text-xs font-semibold text-ink block">
          {locale === "zh" ? "排版风格呈现：" : "Layout Style:"}
        </label>
        <div className="grid grid-cols-2 sm:grid-cols-2 gap-2">
          {HOTLIST_AVAILABLE_STYLES.map((s) => {
            const isSelected = style === s.id;
            return (
              <button
                key={s.id}
                type="button"
                onClick={() => setStyle(s.id)}
                className={`p-2.5 rounded-sm border text-left transition-all flex flex-col justify-between ${
                  isSelected
                    ? "border-ink bg-paper-dark font-medium shadow-2xs"
                    : "border-ink/15 bg-white hover:border-ink/40"
                }`}
              >
                <div>
                  <div className="text-xs font-bold text-ink">{s.label}</div>
                  <div className="text-[10px] text-ink-light mt-0.5">{s.desc}</div>
                </div>
                <div className="mt-2 flex justify-end">
                  <span
                    className={`w-3.5 h-3.5 rounded-full border flex items-center justify-center text-[9px] ${
                      isSelected ? "border-ink bg-ink text-white" : "border-ink/30"
                    }`}
                  >
                    {isSelected ? "●" : ""}
                  </span>
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* Platform multiselect (only for aggregated HOTLIST mode) */}
      {!isStandalone && (
        <div className="space-y-2">
          <label className="text-xs font-semibold text-ink block">
            {locale === "zh" ? "选择展示的热榜平台（支持多选）：" : "Select Platforms (Multi-select):"}
          </label>
          <div className="grid grid-cols-2 sm:grid-cols-2 gap-2 max-h-56 overflow-y-auto pr-1">
          {HOTLIST_AVAILABLE_PLATFORMS.map((p) => {
            const isSelected = platforms.includes(p.id);
            return (
              <button
                key={p.id}
                type="button"
                onClick={() => {
                  if (isSelected) {
                    if (platforms.length > 1) {
                      setPlatforms(platforms.filter((x) => x !== p.id));
                    }
                  } else {
                    setPlatforms([...platforms, p.id]);
                  }
                }}
                className={`p-2.5 rounded-sm border text-left transition-all flex items-center justify-between ${
                  isSelected
                    ? "border-ink bg-paper-dark font-medium shadow-2xs"
                    : "border-ink/15 bg-white hover:border-ink/40"
                }`}
              >
                <div className="min-w-0 pr-2">
                  <div className="text-xs font-bold text-ink truncate">{p.label}</div>
                  <div className="text-[10px] text-ink-light truncate">{p.desc}</div>
                </div>
                <div
                  className={`w-4 h-4 shrink-0 rounded-xs border flex items-center justify-center text-[10px] ${
                    isSelected ? "border-ink bg-ink text-white" : "border-ink/20"
                  }`}
                >
                  {isSelected ? "✓" : ""}
                </div>
              </button>
            );
          })}
        </div>
      </div>
      )}

      <div className="pt-2 flex items-center justify-between border-t border-ink/10">
        {isStandalone ? (
          <div className="text-xs text-ink-light font-medium">
            {locale === "zh" ? "✦ 排行榜前 8 项完整呈现 · 支持图文展示" : "✦ Full top 8 items · Illustrated cover card"}
          </div>
        ) : (
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => setPlatforms(HOTLIST_AVAILABLE_PLATFORMS.map((p) => p.id))}
              className="text-xs text-ink-light hover:text-ink underline"
            >
              {locale === "zh" ? "全选" : "Select All"}
            </button>
            <span className="text-ink/20">|</span>
            <button
              type="button"
              onClick={() => setPlatforms(["zhihu", "weibo", "bilibili"])}
              className="text-xs text-ink-light hover:text-ink underline"
            >
              {locale === "zh" ? "重置默认" : "Reset"}
            </button>
          </div>
        )}

        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={onClose}>
            {locale === "zh" ? "取消" : "Cancel"}
          </Button>
          <Button
            size="sm"
            onClick={async () => {
              onClose();
              if (isStandalone) {
                await onSubmit([], style);
              } else {
                await onSubmit(platforms, style);
              }
            }}
            disabled={previewLoading}
            className="bg-ink text-white hover:bg-ink/90"
          >
            {locale === "zh" ? "应用并预览热点" : "Apply & Preview"}
          </Button>
        </div>
      </div>
    </div>
  );
}
