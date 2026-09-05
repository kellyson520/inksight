"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Coins, Check, TrendingUp } from "lucide-react";
import { POPULAR_GOLDS } from "../types";

interface GoldConfigProps {
  initialSymbol: string;
  locale: string;
  previewLoading: boolean;
  onClose: () => void;
  onSubmit: (symbol: string) => Promise<void>;
}

export function GoldConfig({
  initialSymbol,
  locale,
  previewLoading,
  onClose,
  onSubmit,
}: GoldConfigProps) {
  const isZh = locale !== "en";
  const [selectedSymbol, setSelectedSymbol] = useState(initialSymbol || "AU0");

  const handleSubmit = async () => {
    await onSubmit(selectedSymbol);
    onClose();
  };

  return (
    <div className="space-y-5">
      {/* 标的卡片选择 */}
      <div className="space-y-3">
        <label className="text-xs font-semibold text-ink-muted uppercase tracking-wider block">
          {isZh ? "选择黄金跟踪标的" : "Select Gold Asset"}
        </label>
        <div className="grid grid-cols-1 gap-2.5">
          {POPULAR_GOLDS.map((gold) => {
            const isSelected = selectedSymbol === gold.sym;
            return (
              <button
                key={gold.sym}
                type="button"
                onClick={() => setSelectedSymbol(gold.sym)}
                className={`flex items-start justify-between p-3 rounded-lg border text-left transition-all ${
                  isSelected
                    ? "border-amber-500 bg-amber-50/50 dark:bg-amber-950/20 shadow-xs"
                    : "border-border hover:border-ink-muted hover:bg-muted/30"
                }`}
              >
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-sm text-ink">{gold.name}</span>
                    <span
                      className={`text-[10px] px-1.5 py-0.5 rounded font-mono font-bold ${
                        isSelected
                          ? "bg-amber-500 text-white"
                          : "bg-muted text-ink-muted"
                      }`}
                    >
                      {gold.sym}
                    </span>
                  </div>
                  <p className="text-xs text-ink-muted leading-relaxed">{gold.desc}</p>
                </div>
                {isSelected && (
                  <div className="w-5 h-5 rounded-full bg-amber-500 text-white flex items-center justify-center shrink-0 mt-0.5">
                    <Check className="w-3 h-3 stroke-[3]" />
                  </div>
                )}
              </button>
            );
          })}
        </div>
      </div>

      {/* 提示信息 */}
      <div className="bg-muted/40 border border-border/80 rounded-lg p-3 text-xs text-ink-muted space-y-1">
        <div className="flex items-center gap-1.5 font-medium text-ink">
          <TrendingUp className="w-3.5 h-3.5 text-amber-500" />
          <span>{isZh ? "分时走势与双源对照" : "Intraday Trend & Dual-quote"}</span>
        </div>
        <p className="leading-relaxed">
          {isZh
            ? "黄金趋势模式内置实时分时走势图与阴影填充，在查看国内克价时联动对照国际美元金价，查看国际金价时联动对照国内折算价。"
            : "Features real-time intraday sparklines with dual-quote reference linking domestic CNY/gram and international USD/oz."}
        </p>
      </div>

      {/* 底部按钮 */}
      <div className="flex justify-end gap-2 pt-2 border-t border-border">
        <Button variant="ghost" onClick={onClose} disabled={previewLoading}>
          {isZh ? "取消" : "Cancel"}
        </Button>
        <Button
          onClick={handleSubmit}
          disabled={previewLoading}
          className="bg-amber-600 hover:bg-amber-700 text-white"
        >
          {previewLoading ? (
            <span>{isZh ? "生成中..." : "Applying..."}</span>
          ) : (
            <span className="flex items-center gap-1.5">
              <Coins className="w-4 h-4" />
              {isZh ? "应用并渲染" : "Apply & Preview"}
            </span>
          )}
        </Button>
      </div>
    </div>
  );
}
