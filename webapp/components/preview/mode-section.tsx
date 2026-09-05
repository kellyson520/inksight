"use client";

import { useState, useEffect, type ReactNode } from "react";
import { ChevronLeft, ChevronRight, Eye, Sliders, type LucideIcon } from "lucide-react";
import { CONFIGURABLE_MODES } from "./types";

interface PaginatedModeSectionProps {
  title: string;
  subtitle?: string;
  icon?: LucideIcon;
  modes: string[];
  currentMode: string;
  onPreview: (m: string) => void;
  onConfigure: (m: string) => void;
  customMeta?: Record<string, { name: string; tip: string; category?: string }>;
  tailItem?: ReactNode;
  locale: string;
  pageSize?: number;
}

export function PaginatedModeSection({
  title,
  subtitle,
  icon: Icon,
  modes,
  currentMode,
  onPreview,
  onConfigure,
  customMeta,
  tailItem,
  locale,
  pageSize = 8,
}: PaginatedModeSectionProps) {
  const [page, setPage] = useState(0);

  const totalSlots = modes.length + (tailItem ? 1 : 0);
  const totalPages = Math.max(1, Math.ceil(totalSlots / pageSize));

  useEffect(() => {
    if (page >= totalPages) {
      setPage(0);
    }
  }, [page, totalPages]);

  if (modes.length === 0 && !tailItem) return null;

  const startIndex = page * pageSize;
  const visibleModes = modes.slice(startIndex, startIndex + pageSize);
  const showTailHere =
    tailItem &&
    startIndex + visibleModes.length <= totalSlots &&
    startIndex + visibleModes.length >= modes.length;

  return (
    <div className="mb-6 rounded-sm border border-ink/10 dark:border-zinc-800/80 bg-white/60 dark:bg-zinc-900/60 p-4 shadow-sm backdrop-blur-xs">
      {/* 容器标题栏与翻页控制 */}
      <div className="flex items-center justify-between gap-3 mb-3.5 pb-2 border-b border-ink/10">
        <div className="flex items-center gap-2">
          {Icon ? <Icon size={16} className="text-ink" /> : null}
          <h4 className="text-sm font-semibold text-ink tracking-tight">{title}</h4>
          <span className="text-[11px] px-1.5 py-0.5 rounded-full bg-ink/5 text-ink-light font-mono">
            {modes.length}
          </span>
          {subtitle ? <span className="text-xs text-ink-light hidden sm:inline">· {subtitle}</span> : null}
        </div>

        {/* 容器翻页切换器 */}
        {totalPages > 1 ? (
          <div className="flex items-center gap-1.5 text-xs text-ink-light">
            <span className="font-mono text-[11px] mr-1">
              {page + 1} / {totalPages}
            </span>
            <button
              onClick={() => setPage((p) => Math.max(0, p - 1))}
              disabled={page === 0}
              className="p-1 rounded hover:bg-ink/10 disabled:opacity-30 disabled:pointer-events-none transition-colors"
              title={locale === "zh" ? "上一页" : "Previous Page"}
            >
              <ChevronLeft size={15} />
            </button>
            <button
              onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
              disabled={page >= totalPages - 1}
              className="p-1 rounded hover:bg-ink/10 disabled:opacity-30 disabled:pointer-events-none transition-colors"
              title={locale === "zh" ? "下一页" : "Next Page"}
            >
              <ChevronRight size={15} />
            </button>
          </div>
        ) : null}
      </div>

      {/* 模式卡片网格 */}
      <div className="grid grid-cols-2 sm:grid-cols-3 xl:grid-cols-4 gap-2.5">
        {visibleModes.map((m) => {
          const meta = customMeta?.[m] || { name: m, tip: "" };
          const isCurrent = currentMode === m;
          const isConfigurable = Boolean(CONFIGURABLE_MODES[m]);

          return (
            <div
              key={m}
              className={`group relative rounded-sm border transition-all text-left flex flex-col justify-between overflow-hidden ${
                isCurrent
                  ? "border-ink dark:border-zinc-400 bg-paper-dark dark:bg-zinc-800 shadow-sm ring-1 ring-ink dark:ring-zinc-400"
                  : "border-ink/15 dark:border-zinc-800 bg-white dark:bg-zinc-900 hover:border-ink/40 dark:hover:border-zinc-700 hover:bg-paper-light dark:hover:bg-zinc-800/60"
              }`}
            >
              {/* 卡片主体：点击即展示 */}
              <button
                onClick={() => onPreview(m)}
                className="w-full p-2.5 text-left flex-1 flex flex-col justify-start"
              >
                <div className="flex items-center justify-between gap-1 w-full mb-1">
                  <span className="text-xs font-bold truncate text-ink">
                    {meta.name}
                  </span>
                  {m === "DISASTER_ALERT" ? (
                    <span className="text-[10px] px-1 py-0.2 rounded bg-red-100 text-red-700 font-medium shrink-0">
                      最高优
                    </span>
                  ) : m === "HOTLIST" ? (
                    <span className="text-[10px] px-1 py-0.2 rounded bg-orange-100 text-orange-700 font-medium shrink-0">
                      多源
                    </span>
                  ) : null}
                </div>
                <p className="text-[11px] text-ink-light line-clamp-2 leading-relaxed">
                  {meta.tip || (locale === "zh" ? "点击快速预览此模式" : "Click to preview this mode")}
                </p>
              </button>

              {/* 操作底栏 */}
              <div className="border-t border-ink/10 dark:border-zinc-800 bg-white/70 dark:bg-zinc-950/70 px-2 py-1 flex items-center justify-between gap-1">
                <button
                  onClick={() => onPreview(m)}
                  className={`text-[11px] font-medium flex items-center gap-1 transition-colors ${
                    isCurrent ? "text-ink font-semibold" : "text-ink-light hover:text-ink"
                  }`}
                >
                  <Eye size={13} />
                  <span>{isCurrent ? (locale === "zh" ? "当前中" : "Active") : (locale === "zh" ? "预览" : "Preview")}</span>
                </button>

                {isConfigurable ? (
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onConfigure(m);
                    }}
                    className="text-[11px] text-ink-light hover:text-ink flex items-center gap-0.5 px-1.5 py-0.5 rounded hover:bg-ink/5 transition-colors"
                    title={locale === "zh" ? "调整此模式参数" : "Configure parameters"}
                  >
                    <Sliders size={12} />
                    <span>{locale === "zh" ? "配置" : "Options"}</span>
                  </button>
                ) : null}
              </div>
            </div>
          );
        })}

        {showTailHere ? tailItem : null}
      </div>
    </div>
  );
}
