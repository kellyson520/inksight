"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { DISASTER_LEVELS, DISASTER_HAZARDS } from "../types";

interface DisasterConfigProps {
  initialLevel: string;
  initialHazard: string;
  locale: string;
  previewLoading: boolean;
  onClose: () => void;
  onSubmit: (override: { level: string; hazard: string; text?: string }) => Promise<void>;
}

export function DisasterConfig({
  initialLevel,
  initialHazard,
  locale,
  previewLoading,
  onClose,
  onSubmit,
}: DisasterConfigProps) {
  const [disasterLevel, setDisasterLevel] = useState(initialLevel || "red");
  const [disasterHazard, setDisasterHazard] = useState(initialHazard || "rainstorm");
  const [disasterCustomText, setDisasterCustomText] = useState("");

  return (
    <div className="space-y-4">
      <div className="text-xs text-ink-light leading-relaxed">
        {locale === "zh"
          ? "国家标准四级预警体系体验：选择预警级别与灾害类型，体验最高优先级全屏紧急避险广播。"
          : "Experience the national standard 4-tier emergency disaster warning system."}
      </div>

      <div className="space-y-1.5">
        <label className="text-xs font-semibold text-ink block">
          {locale === "zh" ? "预警级别（严重度）：" : "Warning Level (Severity):"}
        </label>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
          {DISASTER_LEVELS.map((lvl) => {
            const isSelected = disasterLevel === lvl.id;
            return (
              <button
                key={lvl.id}
                type="button"
                onClick={() => setDisasterLevel(lvl.id)}
                className={`p-2 rounded-sm border text-center transition-all ${
                  isSelected
                    ? "border-ink bg-ink text-white font-bold shadow-xs"
                    : "border-ink/20 bg-white text-ink hover:border-ink/40"
                }`}
              >
                <div className="text-xs">{lvl.label}</div>
                <div className={`text-[10px] ${isSelected ? "text-white/80" : "text-ink-light"}`}>
                  {lvl.roman}
                </div>
              </button>
            );
          })}
        </div>
      </div>

      <div className="space-y-1.5">
        <label className="text-xs font-semibold text-ink block">
          {locale === "zh" ? "灾害种类（12大类手绘矢量图标）：" : "Disaster Hazard Type:"}
        </label>
        <div className="grid grid-cols-3 sm:grid-cols-4 gap-1.5">
          {DISASTER_HAZARDS.map((h) => {
            const isSelected = disasterHazard === h.id;
            return (
              <button
                key={h.id}
                type="button"
                onClick={() => setDisasterHazard(h.id)}
                className={`px-2 py-1.5 rounded-sm border text-xs text-center transition-all ${
                  isSelected
                    ? "border-ink bg-paper-dark font-bold ring-1 ring-ink text-ink"
                    : "border-ink/15 bg-white text-ink hover:border-ink/40"
                }`}
              >
                {h.label}
              </button>
            );
          })}
        </div>
      </div>

      <div className="space-y-1">
        <label className="text-xs font-semibold text-ink block">
          {locale === "zh" ? "通报说明文本（可选）：" : "Custom Alert Text (Optional):"}
        </label>
        <textarea
          value={disasterCustomText}
          onChange={(e) => setDisasterCustomText(e.target.value)}
          placeholder={locale === "zh" ? "留空使用气象台官方标准通告..." : "Leave empty to use official text..."}
          rows={2}
          className="w-full rounded-sm border border-ink/20 p-2 text-xs bg-white"
        />
      </div>

      <div className="pt-3 flex items-center justify-end gap-2 border-t border-ink/10">
        <Button variant="outline" size="sm" onClick={onClose}>
          {locale === "zh" ? "取消" : "Cancel"}
        </Button>
        <Button
          size="sm"
          onClick={async () => {
            onClose();
            await onSubmit({
              level: disasterLevel,
              hazard: disasterHazard,
              text: disasterCustomText.trim(),
            });
          }}
          disabled={previewLoading}
          className="bg-red-600 text-white hover:bg-red-700"
        >
          {locale === "zh" ? "立即预览紧急预警" : "Preview Disaster Alert"}
        </Button>
      </div>
    </div>
  );
}
