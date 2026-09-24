"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Headphones, Bell, Check } from "lucide-react";

interface GcoresPodcastConfigProps {
  initialProgram?: string;
  locale: string;
  previewLoading: boolean;
  onClose: () => void;
  onSubmit: (override: Record<string, unknown>) => Promise<void>;
}

export function GcoresPodcastConfig({
  initialProgram = "ALL",
  locale,
  previewLoading,
  onClose,
  onSubmit,
}: GcoresPodcastConfigProps) {
  const isZh = locale !== "en";
  const [selectedProgram, setSelectedProgram] = useState(initialProgram || "ALL");

  const programs = [
    { key: "ALL", name: isZh ? "全部栏目" : "All Episodes", desc: isZh ? "实时更新最新一期电台节目" : "Latest podcast episode across all channels" },
    { key: "PRO", name: "Gadio Pro", desc: isZh ? "硬核游戏开发、深度文化与行业对谈" : "Deep dives, culture, and core game development" },
    { key: "LIFE", name: "Gadio Life", desc: isZh ? "主播日常杂谈、生活见闻与轻松唠嗑" : "Casual stories, life chat, and leisure topics" },
    { key: "MUSIC", name: "Gadio Music", desc: isZh ? "游戏原声、经典曲目鉴赏与音乐专栏" : "Soundtracks, classical tunes, and music specials" },
  ];

  const handleSubmit = async () => {
    await onSubmit({ program: selectedProgram });
    onClose();
  };

  return (
    <div className="space-y-4">
      <label className="text-xs font-semibold text-ink-muted uppercase tracking-wider block">
        {isZh ? "选择机核播客栏目" : "Select Podcast Category"}
      </label>
      <div className="grid grid-cols-1 gap-2">
        {programs.map((p) => {
          const isSelected = selectedProgram === p.key;
          return (
            <button
              key={p.key}
              type="button"
              onClick={() => setSelectedProgram(p.key)}
              className={`flex items-start justify-between p-3 rounded-lg border text-left transition-all ${
                isSelected
                  ? "border-red-600 bg-red-50/50 dark:bg-red-950/20 shadow-xs"
                  : "border-border hover:border-ink-muted hover:bg-muted/30"
              }`}
            >
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span className="font-semibold text-sm text-ink">{p.name}</span>
                  {isSelected && (
                    <span className="bg-red-600 text-white text-[10px] px-1.5 py-0.5 rounded font-bold">
                      {isZh ? "已选" : "Selected"}
                    </span>
                  )}
                </div>
                <p className="text-xs text-ink-light">{p.desc}</p>
              </div>
              {isSelected && <Check size={16} className="text-red-600 mt-1 shrink-0" />}
            </button>
          );
        })}
      </div>
      <div className="pt-3 flex items-center justify-end gap-2 border-t border-ink/10">
        <Button variant="outline" size="sm" onClick={onClose} disabled={previewLoading}>
          {isZh ? "取消" : "Cancel"}
        </Button>
        <Button size="sm" onClick={handleSubmit} disabled={previewLoading}>
          {isZh ? "保存并预览" : "Save & Preview"}
        </Button>
      </div>
    </div>
  );
}

interface MiyousheNewsConfigProps {
  initialGame?: string;
  locale: string;
  previewLoading: boolean;
  onClose: () => void;
  onSubmit: (override: Record<string, unknown>) => Promise<void>;
}

export function MiyousheNewsConfig({
  initialGame = "GENSHIN",
  locale,
  previewLoading,
  onClose,
  onSubmit,
}: MiyousheNewsConfigProps) {
  const isZh = locale !== "en";
  const [selectedGame, setSelectedGame] = useState(initialGame || "GENSHIN");

  const games = [
    { key: "GENSHIN", name: isZh ? "原神" : "Genshin Impact", desc: isZh ? "提瓦特大陆最新活动与官方公告" : "Latest Teyvat events and notices" },
    { key: "STAR_RAIL", name: isZh ? "崩坏：星穹铁道" : "Honkai: Star Rail", desc: isZh ? "银河铁道发车动态与版本情报" : "Astral Express updates and patch news" },
    { key: "ZZZ", name: isZh ? "绝区零" : "Zenless Zone Zero", desc: isZh ? "新艾利都街区活动与降噪测试速递" : "New Eridu urban notices and events" },
    { key: "HONKAI3", name: isZh ? "崩坏3" : "Honkai Impact 3rd", desc: isZh ? "崩坏世界战舰指令与女武神动态" : "Hyperion ship logs and updates" },
  ];

  const handleSubmit = async () => {
    await onSubmit({ game: selectedGame });
    onClose();
  };

  return (
    <div className="space-y-4">
      <label className="text-xs font-semibold text-ink-muted uppercase tracking-wider block">
        {isZh ? "关注的米家游戏" : "Select Focus Game"}
      </label>
      <div className="grid grid-cols-1 gap-2">
        {games.map((g) => {
          const isSelected = selectedGame === g.key;
          return (
            <button
              key={g.key}
              type="button"
              onClick={() => setSelectedGame(g.key)}
              className={`flex items-start justify-between p-3 rounded-lg border text-left transition-all ${
                isSelected
                  ? "border-blue-600 bg-blue-50/50 dark:bg-blue-950/20 shadow-xs"
                  : "border-border hover:border-ink-muted hover:bg-muted/30"
              }`}
            >
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span className="font-semibold text-sm text-ink">{g.name}</span>
                  {isSelected && (
                    <span className="bg-blue-600 text-white text-[10px] px-1.5 py-0.5 rounded font-bold">
                      {isZh ? "已选" : "Selected"}
                    </span>
                  )}
                </div>
                <p className="text-xs text-ink-light">{g.desc}</p>
              </div>
              {isSelected && <Check size={16} className="text-blue-600 mt-1 shrink-0" />}
            </button>
          );
        })}
      </div>
      <div className="pt-3 flex items-center justify-end gap-2 border-t border-ink/10">
        <Button variant="outline" size="sm" onClick={onClose} disabled={previewLoading}>
          {isZh ? "取消" : "Cancel"}
        </Button>
        <Button size="sm" onClick={handleSubmit} disabled={previewLoading}>
          {isZh ? "保存并预览" : "Save & Preview"}
        </Button>
      </div>
    </div>
  );
}
