"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Film, Check, Sparkles } from "lucide-react";
import { DOUBAN_MOVIE_CATEGORIES } from "../types";

interface DoubanMovieConfigProps {
  initialCategory: string;
  locale: string;
  previewLoading: boolean;
  onClose: () => void;
  onSubmit: (category: string) => Promise<void>;
}

export function DoubanMovieConfig({
  initialCategory,
  locale,
  previewLoading,
  onClose,
  onSubmit,
}: DoubanMovieConfigProps) {
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
          {isZh ? "选择电影分类与榜单" : "Select Movie Category & Ranking"}
        </label>
        <div className="grid grid-cols-1 gap-2.5">
          {DOUBAN_MOVIE_CATEGORIES.map((cat) => {
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
                <div className="pt-1 pl-2">
                  <div
                    className={`w-5 h-5 rounded-full flex items-center justify-center border transition-all ${
                      isSelected
                        ? "border-emerald-600 bg-emerald-600 text-white"
                        : "border-border"
                    }`}
                  >
                    {isSelected && <Check size={12} strokeWidth={3} />}
                  </div>
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* 提示信息 */}
      <div className="p-3 bg-muted/40 rounded-lg text-xs text-ink-muted leading-relaxed flex items-center gap-2">
        <Sparkles size={14} className="shrink-0 text-emerald-600" />
        <span>
          {isZh
            ? "墨水屏排版采用微信读书同款艺术布局：右侧高清电影海报，左侧电影名、年份导演与影评推荐理由。"
            : "E-ink layout features posters on the right with title, director, and reviews on the left."}
        </span>
      </div>

      {/* 底部操作栏 */}
      <div className="flex items-center justify-end gap-3 pt-2">
        <Button variant="ghost" onClick={onClose} disabled={previewLoading}>
          {isZh ? "取消" : "Cancel"}
        </Button>
        <Button
          onClick={handleSubmit}
          disabled={previewLoading}
          className="bg-emerald-600 hover:bg-emerald-700 text-white flex items-center gap-1.5"
        >
          <Film size={14} />
          <span>{isZh ? "确认应用" : "Apply"}</span>
        </Button>
      </div>
    </div>
  );
}
