"use client";

import { useState } from "react";
import {
  ChevronDown,
  Eye,
  LayoutGrid,
  Plus,
  Trash2,
  Heart,
  Briefcase,
  Newspaper,
  Sparkles,
  Layers,
  Search,
  Check,
  Settings,
  Sliders,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ColorSelect } from "@/components/ui/color-select";
import { ScreenSizeSelect } from "@/components/ui/screen-size-select";
import { CONFIGURABLE_MODES } from "@/components/preview/types";

type ModeMeta = Record<string, { name: string; tip: string }>;

type ModeSelectorProps = {
  tr: (zh: string, en: string) => string;
  selectedModes: Set<string>;
  customModes: string[];
  customModeMeta: ModeMeta;
  modeMeta: ModeMeta;
  coreModes: string[];
  extraModes: string[];
  handleModePreview: (mode: string) => void;
  handleModeApply: (mode: string) => void;
  handleCustomModeDelete: (mode: string) => void;
  onCreateCustomMode: () => void;
  onOpenConfigModal?: (mode: string) => void;
  previewColors?: number;
  onColorsChange?: (v: number) => void;
  previewWidth?: number;
  previewHeight?: number;
  onScreenSizeChange?: (w: number, h: number) => void;
};

type StudioTab = "all" | "life" | "productivity" | "news" | "studio";

const STUDIO_CATEGORIES_CONFIG: Record<string, StudioTab> = {
  // 资讯与热点
  HOTLIST: "news",
  DISASTER_ALERT: "news",
  RSS: "news",
  CRYPTO: "news",
  GOLD: "news",
  MARKET: "news",
  THISDAY: "news",
  BIAS: "news",
  MOYU: "news",
  // 效率工作
  TODO: "productivity",
  TIMETABLE: "productivity",
  CALENDAR: "productivity",
  COUNTDOWN: "productivity",
  HABIT: "productivity",
  FOCUS: "productivity",
  GITHUB: "productivity",
  POMODORO: "productivity",
  SERVER_STATUS: "productivity",
  CPA_QUOTA: "productivity",
  // 生活日常
  CLOCK: "life",
  WEATHER: "life",
  DAILY: "life",
  STOIC: "life",
  MY_QUOTE: "life",
  HEALTH: "life",
  AIR: "life",
  LIFEBAR: "lifebar" as never,
  MEMO: "life",
  DRINK_WATER: "life",
  WECHAT_READ: "life",
  // 灵感与创作
  WORD_OF_THE_DAY: "studio",
  LETTER: "studio",
  RIDDLE: "studio",
  ROAST: "studio",
  ZEN: "studio",
  STORY: "studio",
  POETRY: "studio",
  QUESTION: "studio",
  CHALLENGE: "studio",
};

export function ModeSelector({
  tr,
  selectedModes,
  customModes,
  customModeMeta,
  modeMeta,
  coreModes,
  extraModes,
  handleModePreview,
  handleModeApply,
  handleCustomModeDelete,
  onCreateCustomMode,
  onOpenConfigModal,
  previewColors,
  onColorsChange,
  previewWidth = 400,
  previewHeight = 300,
  onScreenSizeChange,
}: ModeSelectorProps) {
  const [activeTab, setActiveTab] = useState<StudioTab>("all");
  const [keyword, setKeyword] = useState("");

  const allBuiltinModes = Array.from(new Set([...coreModes, ...extraModes]));

  const getCategory = (modeId: string): StudioTab => {
    if (customModes.includes(modeId)) return "studio";
    return STUDIO_CATEGORIES_CONFIG[modeId] || "life";
  };

  const filterModes = (modes: string[]) => {
    return modes.filter((m) => {
      const meta = modeMeta[m] || customModeMeta[m] || { name: m, tip: "" };
      const matchesTab = activeTab === "all" || getCategory(m) === activeTab;
      const matchesKw =
        !keyword.trim() ||
        meta.name.toLowerCase().includes(keyword.toLowerCase()) ||
        meta.tip.toLowerCase().includes(keyword.toLowerCase()) ||
        m.toLowerCase().includes(keyword.toLowerCase());
      return matchesTab && matchesKw;
    });
  };

  const displayedBuiltins = filterModes(allBuiltinModes);
  const displayedCustoms = filterModes(customModes);

  return (
    <Card className="border-ink/10 shadow-xs">
      <CardHeader className="pb-3 border-b border-ink/10">
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
          <CardTitle className="flex items-center gap-2 text-lg font-serif">
            <LayoutGrid size={18} /> {tr("组件与内容模式", "Components & Studio Modes")}
          </CardTitle>
          <div className="flex items-center gap-2 flex-wrap">
            {onColorsChange && previewColors !== undefined && (
              <ColorSelect value={previewColors} onChange={onColorsChange} tr={tr} />
            )}
            {onScreenSizeChange && previewWidth !== undefined && previewHeight !== undefined && (
              <ScreenSizeSelect width={previewWidth} height={previewHeight} onChange={onScreenSizeChange} tr={tr} />
            )}
          </div>
        </div>

        {/* 顶部统一分类导航栏与搜索框 */}
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-2.5 pt-3">
          <div className="flex items-center gap-1 overflow-x-auto pb-1 sm:pb-0">
            {[
              { id: "all", label: tr("全部", "All"), icon: Layers },
              { id: "life", label: tr("生活日常", "Life"), icon: Heart },
              { id: "productivity", label: tr("效率工作", "Productivity"), icon: Briefcase },
              { id: "news", label: tr("资讯热点", "News & Feeds"), icon: Newspaper },
              { id: "studio", label: tr("灵感创作", "Studio"), icon: Sparkles },
            ].map((tab) => {
              const isActive = activeTab === tab.id;
              const Icon = tab.icon;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id as StudioTab)}
                  className={`px-2.5 py-1.5 rounded-sm text-xs font-medium transition-all whitespace-nowrap flex items-center gap-1.5 ${
                    isActive
                      ? "bg-ink text-white shadow-2xs font-semibold"
                      : "text-ink-light hover:text-ink hover:bg-paper-dark"
                  }`}
                >
                  <Icon size={13} />
                  <span>{tab.label}</span>
                </button>
              );
            })}
          </div>

          <div className="relative w-full sm:w-44">
            <Search size={13} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-ink-light" />
            <input
              type="text"
              value={keyword}
              onChange={(e) => setKeyword(e.target.value)}
              placeholder={tr("搜索模式...", "Filter modes...")}
              className="w-full pl-7 pr-2.5 py-1 text-xs rounded-sm border border-ink/20 bg-white focus:outline-hidden focus:border-ink transition-colors"
            />
          </div>
        </div>
      </CardHeader>

      <CardContent className="pt-4 space-y-4">
        {/* 内置组件网格 */}
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5">
          {displayedBuiltins.map((mode) => {
            const meta = modeMeta[mode] || { name: mode, tip: "" };
            const isSelected = selectedModes.has(mode);
            const isConfigurable = Boolean(CONFIGURABLE_MODES[mode.toUpperCase()]);

            return (
              <div
                key={mode}
                className={`group relative rounded-sm border transition-all flex flex-col justify-between overflow-hidden ${
                  isSelected
                    ? "border-ink bg-paper-dark/60 shadow-2xs"
                    : "border-ink/15 bg-white hover:border-ink/40"
                }`}
              >
                {/* 卡片头部与说明 */}
                <div
                  onClick={() => handleModePreview(mode)}
                  className="p-3 cursor-pointer select-none flex-1 flex flex-col justify-between"
                  title={tr("点击在右侧即时渲染预览", "Click to preview on the right")}
                >
                  <div>
                    <div className="flex items-center justify-between gap-1">
                      <span className="text-xs font-bold text-ink truncate">{meta.name}</span>
                      <div className="flex items-center gap-1 shrink-0">
                        {isConfigurable && onOpenConfigModal ? (
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              onOpenConfigModal(mode);
                            }}
                            className="text-[10px] text-ink/80 hover:text-ink hover:bg-paper-dark font-medium bg-white px-1.5 py-0.5 rounded-xs border border-ink/20 hover:border-ink flex items-center gap-0.5 transition-all"
                            title={tr("点击调节此模式的参数配置", "Configure mode parameters")}
                          >
                            <Sliders size={10} />
                            <span>{tr("调节", "Config")}</span>
                          </button>
                        ) : null}
                        {isSelected ? (
                          <span className="shrink-0 flex items-center gap-0.5 text-[10px] font-semibold text-emerald-800 bg-emerald-100/90 px-1.5 py-0.2 rounded-xs border border-emerald-300">
                            <Check size={10} /> {tr("已加入", "Active")}
                          </span>
                        ) : null}
                      </div>
                    </div>
                    <p className="text-[11px] text-ink-light mt-1 line-clamp-2 leading-relaxed">
                      {meta.tip}
                    </p>
                  </div>
                </div>

                {/* 卡片底部操作按钮栏 */}
                <div className="border-t border-ink/10 bg-paper-light/70 px-2 py-1.5 flex items-center justify-between text-xs">
                  <button
                    type="button"
                    onClick={() => handleModePreview(mode)}
                    className="text-ink-light hover:text-ink flex items-center gap-1 font-medium transition-colors"
                  >
                    <Eye size={12} />
                    <span>{tr("预览", "Preview")}</span>
                  </button>

                  <div className="flex items-center gap-1.5">
                    <button
                      type="button"
                      onClick={() => handleModeApply(mode)}
                      className={`px-2 py-0.5 rounded-sm text-[11px] font-semibold transition-colors ${
                        isSelected
                          ? "bg-ink/10 text-ink hover:bg-red-100 hover:text-red-700"
                          : "bg-ink text-white hover:bg-ink-light"
                      }`}
                    >
                      {isSelected ? tr("移除", "Remove") : tr("加入轮播", "Add")}
                    </button>
                  </div>
                </div>
              </div>
            );
          })}

          {/* 自定义模式网格 */}
          {displayedCustoms.map((mode) => {
            const meta = customModeMeta[mode] || { name: mode, tip: "" };
            const isSelected = selectedModes.has(mode);

            return (
              <div
                key={mode}
                className={`group relative rounded-sm border transition-all flex flex-col justify-between overflow-hidden ${
                  isSelected
                    ? "border-ink bg-paper-dark/60 shadow-2xs"
                    : "border-ink/15 bg-white hover:border-ink/40"
                }`}
              >
                <div
                  onClick={() => handleModePreview(mode)}
                  className="p-3 cursor-pointer select-none flex-1 flex flex-col justify-between"
                >
                  <div>
                    <div className="flex items-center justify-between gap-1">
                      <span className="text-xs font-bold text-ink truncate">{meta.name}</span>
                      <span className="shrink-0 text-[10px] text-ink-light font-mono px-1 py-0.2 rounded-xs bg-paper-dark">
                        Studio
                      </span>
                    </div>
                    <p className="text-[11px] text-ink-light mt-1 line-clamp-2 leading-relaxed">
                      {meta.tip || tr("用户自定义组件", "Custom user component")}
                    </p>
                  </div>
                </div>

                <div className="border-t border-ink/10 bg-paper-light/70 px-2 py-1.5 flex items-center justify-between text-xs">
                  <button
                    type="button"
                    onClick={() => handleModePreview(mode)}
                    className="text-ink-light hover:text-ink flex items-center gap-1 font-medium transition-colors"
                  >
                    <Eye size={12} />
                    <span>{tr("预览", "Preview")}</span>
                  </button>

                  <div className="flex items-center gap-1.5">
                    <button
                      type="button"
                      onClick={() => handleCustomModeDelete(mode)}
                      className="text-ink-light hover:text-red-600 p-1 rounded-sm hover:bg-red-50 transition-colors"
                      title={tr("删除模式", "Delete mode")}
                    >
                      <Trash2 size={12} />
                    </button>
                    <button
                      type="button"
                      onClick={() => handleModeApply(mode)}
                      className={`px-2 py-0.5 rounded-sm text-[11px] font-semibold transition-colors ${
                        isSelected
                          ? "bg-ink/10 text-ink hover:bg-red-100 hover:text-red-700"
                          : "bg-ink text-white hover:bg-ink-light"
                      }`}
                    >
                      {isSelected ? tr("移除", "Remove") : tr("加入轮播", "Add")}
                    </button>
                  </div>
                </div>
              </div>
            );
          })}

          {/* 新建自定义组件入口 */}
          <button
            type="button"
            onClick={onCreateCustomMode}
            className="rounded-sm border border-dashed border-ink/25 bg-white/60 p-4 min-h-[96px] flex flex-col items-center justify-center text-ink-light hover:border-ink hover:bg-paper-dark transition-all group"
          >
            <Plus size={18} className="text-ink-light group-hover:text-ink transition-colors mb-1" />
            <span className="text-xs font-semibold text-ink group-hover:underline">
              {tr("新建自定义模式", "New Studio Mode")}
            </span>
            <span className="text-[10px] text-ink-light mt-0.5">
              {tr("AI 提示词或自由搭配", "AI Prompt or Layout")}
            </span>
          </button>
        </div>
      </CardContent>
    </Card>
  );
}
