"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { HOTLIST_AVAILABLE_PLATFORMS, HOTLIST_AVAILABLE_STYLES } from "../types";

interface HotlistConfigProps {
  initialPlatforms: string[];
  initialStyle?: string;
  locale: string;
  previewLoading: boolean;
  onClose: () => void;
  onSubmit: (platforms: string[], style: string) => Promise<void>;
}

export function HotlistConfig({
  initialPlatforms,
  initialStyle = "dense_grid",
  locale,
  previewLoading,
  onClose,
  onSubmit,
}: HotlistConfigProps) {
  const [platforms, setPlatforms] = useState<string[]>(
    initialPlatforms.length > 0 ? initialPlatforms : ["zhihu", "weibo", "bilibili"]
  );
  const [style, setStyle] = useState<string>(initialStyle);

  return (
    <div className="space-y-4">
      <div className="text-xs text-ink-light leading-relaxed">
        {locale === "zh"
          ? "支持网易云音乐、豆瓣电影、抖音、微信、知乎、微博、B站、36氪等 13 大主流平台多选聚合与三种排版风格！系统将并发抓取并结构化呈现。"
          : "Supports 13 mainstream platforms (NetEase, Douban, Douyin, WeChat, Zhihu, etc.) and 3 e-ink visual layouts with concurrent aggregation."}
      </div>

      {/* Style selector */}
      <div className="space-y-2">
        <label className="text-xs font-semibold text-ink block">
          {locale === "zh" ? "排版风格呈现：" : "Layout Style:"}
        </label>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
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

      {/* Platform multiselect */}
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

      <div className="pt-2 flex items-center justify-between border-t border-ink/10">
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

        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={onClose}>
            {locale === "zh" ? "取消" : "Cancel"}
          </Button>
          <Button
            size="sm"
            onClick={async () => {
              onClose();
              await onSubmit(platforms, style);
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
