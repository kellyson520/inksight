"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { HOTLIST_AVAILABLE_PLATFORMS } from "../types";

interface HotlistConfigProps {
  initialPlatforms: string[];
  locale: string;
  previewLoading: boolean;
  onClose: () => void;
  onSubmit: (platforms: string[]) => Promise<void>;
}

export function HotlistConfig({
  initialPlatforms,
  locale,
  previewLoading,
  onClose,
  onSubmit,
}: HotlistConfigProps) {
  const [platforms, setPlatforms] = useState<string[]>(
    initialPlatforms.length > 0 ? initialPlatforms : ["zhihu", "weibo", "bilibili"]
  );

  return (
    <div className="space-y-4">
      <div className="text-xs text-ink-light leading-relaxed">
        {locale === "zh"
          ? "支持多选聚合！点击下方平台可自由组合勾选，系统将并发抓取所选平台的精选热搜并交错聚合展示于墨水屏。"
          : "Multi-select supported! Select multiple platforms below to fetch and aggregate trending topics together."}
      </div>

      <div className="space-y-2">
        <label className="text-xs font-semibold text-ink block">
          {locale === "zh" ? "选择展示的热榜平台（支持多选）：" : "Select Platforms (Multi-select):"}
        </label>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
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
                <div>
                  <div className="text-xs font-bold text-ink">{p.label}</div>
                  <div className="text-[10px] text-ink-light">{p.desc}</div>
                </div>
                <div
                  className={`w-4 h-4 rounded-xs border flex items-center justify-center text-[10px] ${
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
        <button
          type="button"
          onClick={() => setPlatforms(["zhihu", "weibo", "bilibili", "baidu", "github"])}
          className="text-xs text-ink-light hover:text-ink underline"
        >
          {locale === "zh" ? "全选所有平台" : "Select All"}
        </button>

        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={onClose}>
            {locale === "zh" ? "取消" : "Cancel"}
          </Button>
          <Button
            size="sm"
            onClick={async () => {
              onClose();
              await onSubmit(platforms);
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
