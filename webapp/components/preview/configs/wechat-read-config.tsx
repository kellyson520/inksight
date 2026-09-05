"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { BookOpen, Check, Sparkles } from "lucide-react";
import { WECHAT_READ_CATEGORIES } from "../types";

interface WeChatReadConfigProps {
  initialCategory: string;
  locale: string;
  previewLoading: boolean;
  onClose: () => void;
  onSubmit: (category: string) => Promise<void>;
}

export function WeChatReadConfig({
  initialCategory,
  locale,
  previewLoading,
  onClose,
  onSubmit,
}: WeChatReadConfigProps) {
  const isZh = locale !== "en";
  const [selectedCategory, setSelectedCategory] = useState(initialCategory || "ALL");

  const handleSubmit = async () => {
    await onSubmit(selectedCategory);
    onClose();
  };

  return (
    <div className="space-y-5">
      {/* 分类选项列表 */}
      <div className="space-y-3">
        <label className="text-xs font-semibold text-ink-muted uppercase tracking-wider block">
          {isZh ? "选择推荐分类" : "Select Recommendation Category"}
        </label>
        <div className="grid grid-cols-1 gap-2.5">
          {WECHAT_READ_CATEGORIES.map((cat) => {
            const isSelected = selectedCategory === cat.key;
            return (
              <button
                key={cat.key}
                type="button"
                onClick={() => setSelectedCategory(cat.key)}
                className={`flex items-start justify-between p-3 rounded-lg border text-left transition-all ${
                  isSelected
                    ? "border-emerald-600 bg-emerald-50/50 dark:bg-emerald-950/20 shadow-xs"
                    : "border-border hover:border-ink-muted hover:bg-muted/30"
                }`}
              >
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-sm text-ink">{cat.name}</span>
                    <span
                      className={`text-[10px] px-1.5 py-0.5 rounded font-mono font-bold ${
                        isSelected
                          ? "bg-emerald-600 text-white"
                          : "bg-muted text-ink-muted"
                      }`}
                    >
                      {cat.key}
                    </span>
                  </div>
                  <p className="text-xs text-ink-muted leading-relaxed">{cat.desc}</p>
                </div>
                {isSelected && (
                  <div className="w-5 h-5 rounded-full bg-emerald-600 text-white flex items-center justify-center shrink-0 mt-0.5">
                    <Check className="w-3 h-3 stroke-[3]" />
                  </div>
                )}
              </button>
            );
          })}
        </div>
      </div>

      {/* 排版特色说明 */}
      <div className="bg-muted/40 border border-border/80 rounded-lg p-3 text-xs text-ink-muted space-y-1">
        <div className="flex items-center gap-1.5 font-medium text-ink">
          <Sparkles className="w-3.5 h-3.5 text-emerald-600" />
          <span>{isZh ? "墨水屏专属排版" : "Optimized E-ink Layout"}</span>
        </div>
        <p className="leading-relaxed">
          {isZh
            ? "右侧展示图书高清封面与墨水屏专用灰度抖动，左侧展示双书名号书名、作者分类、核心推荐理由与微信读书在读指数。"
            : "Displays cover image on the right with custom e-ink dithering, and title, author, review and reading stats on the left."}
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
          className="bg-emerald-700 hover:bg-emerald-800 text-white"
        >
          {previewLoading ? (
            <span>{isZh ? "生成中..." : "Applying..."}</span>
          ) : (
            <span className="flex items-center gap-1.5">
              <BookOpen className="w-4 h-4" />
              {isZh ? "应用并渲染" : "Apply & Preview"}
            </span>
          )}
        </Button>
      </div>
    </div>
  );
}
