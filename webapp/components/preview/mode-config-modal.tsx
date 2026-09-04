"use client";

import { Sliders } from "lucide-react";
import { Button } from "@/components/ui/button";
import { HotlistConfig } from "./configs/hotlist-config";
import { DisasterConfig } from "./configs/disaster-config";
import { WeatherConfig } from "./configs/weather-config";
import { CryptoStockConfig } from "./configs/crypto-stock-config";
import { ServerStatusConfig } from "./configs/server-status-config";
import {
  MemoConfig,
  RssConfig,
  QuoteConfig,
  CountdownConfig,
  HabitConfig,
  LifebarConfig,
  WebhookConfig,
  PomodoroConfig,
  DrinkWaterConfig,
} from "./configs/lifestyle-configs";

interface ModeConfigModalProps {
  modal: {
    type:
      | "quote"
      | "weather"
      | "memo"
      | "countdown"
      | "habit"
      | "lifebar"
      | "calendar"
      | "timetable"
      | "rss"
      | "crypto"
      | "hotlist"
      | "disaster"
      | "webhook"
      | "pomodoro"
      | "drink_water"
      | "server_status";
    modeId: string;
  };
  locale: string;
  previewLoading: boolean;
  onClose: () => void;
  onSubmit: (modeId: string, override: Record<string, unknown>) => Promise<void>;
  initialHotlistPlatforms: string[];
  initialHotlistStyle?: string;
  initialDisasterLevel: string;
  initialDisasterHazard: string;
  initialDisasterCity?: string;
  initialRssFeedUrl: string;
  initialCryptoSymbol: string;
}

export function ModeConfigModal({
  modal,
  locale,
  previewLoading,
  onClose,
  onSubmit,
  initialHotlistPlatforms,
  initialHotlistStyle = "dense_grid",
  initialDisasterLevel,
  initialDisasterHazard,
  initialDisasterCity = "",
  initialRssFeedUrl,
  initialCryptoSymbol,
}: ModeConfigModalProps) {
  const getModalTitle = () => {
    switch (modal.type) {
      case "hotlist":
        return locale === "zh" ? "全网热点 · 多平台多选与聚合" : "Trending Topics Configuration";
      case "disaster":
        return locale === "zh" ? "自然灾害预警 · 四级预警体验" : "Disaster Warning Alert Experience";
      case "weather":
        return locale === "zh" ? "天气预报设置" : "Weather Settings";
      case "memo":
        return locale === "zh" ? "便签内容设置" : "Memo Settings";
      case "quote":
        return locale === "zh" ? "自定义语录设置" : "Quote Settings";
      case "countdown":
        return locale === "zh" ? "倒计时设置" : "Countdown Settings";
      case "habit":
        return locale === "zh" ? "习惯打卡项" : "Habit Tracker";
      case "lifebar":
        return locale === "zh" ? "人生进度条" : "Life Progress";
      case "rss":
        return locale === "zh" ? "RSS 订阅设置" : "RSS Settings";
      case "crypto":
        return locale === "zh" ? "资产与股票行情设置" : "Stock & Asset Settings";
      case "webhook":
        return locale === "zh" ? "开放数据卡片模拟" : "Webhook Card Simulator";
      case "pomodoro":
        return locale === "zh" ? "专注番茄钟设置" : "Focus Pomodoro Settings";
      case "drink_water":
        return locale === "zh" ? "健康补水设置" : "Hydration Settings";
      case "server_status":
        return locale === "zh" ? "服务器与主机性能监控" : "Server Status Monitor";
      default:
        return locale === "zh" ? "模式参数设置" : "Mode Settings";
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/45 backdrop-blur-2xs" onClick={onClose} />
      <div className="relative w-full max-w-lg rounded-sm border border-ink/20 bg-white shadow-2xl overflow-hidden">
        {/* Modal Header */}
        <div className="px-5 py-3.5 border-b border-ink/10 flex items-center justify-between bg-paper-dark">
          <div className="text-sm font-bold text-ink flex items-center gap-2">
            <Sliders size={16} />
            <span>{getModalTitle()}</span>
          </div>
          <button className="text-ink-light hover:text-ink text-sm p-1" onClick={onClose}>
            ✕
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-5 space-y-4 max-h-[75vh] overflow-y-auto">
          {modal.type === "hotlist" ? (
            <HotlistConfig
              initialPlatforms={initialHotlistPlatforms}
              initialStyle={initialHotlistStyle}
              locale={locale}
              previewLoading={previewLoading}
              onClose={onClose}
              onSubmit={async (platforms, style) => {
                await onSubmit("HOTLIST", { platforms, style });
              }}
            />
          ) : modal.type === "disaster" ? (
            <DisasterConfig
              initialLevel={initialDisasterLevel}
              initialHazard={initialDisasterHazard}
              initialCity={initialDisasterCity}
              locale={locale}
              previewLoading={previewLoading}
              onClose={onClose}
              onSubmit={async (override) => {
                await onSubmit("DISASTER_ALERT", override);
              }}
            />
          ) : modal.type === "weather" ? (
            <WeatherConfig
              initialLocation={{ city: "杭州" }}
              locale={locale}
              previewLoading={previewLoading}
              onClose={onClose}
              onSubmit={async (override) => {
                await onSubmit("WEATHER", override);
              }}
            />
          ) : modal.type === "memo" ? (
            <MemoConfig
              locale={locale}
              previewLoading={previewLoading}
              onClose={onClose}
              onSubmit={async (override) => {
                await onSubmit("MEMO", override);
              }}
            />
          ) : modal.type === "rss" ? (
            <RssConfig
              initialUrl={initialRssFeedUrl}
              onClose={onClose}
              onSubmit={async (override) => {
                await onSubmit("RSS", override);
              }}
            />
          ) : modal.type === "crypto" ? (
            <CryptoStockConfig
              initialSymbol={initialCryptoSymbol}
              locale={locale}
              previewLoading={previewLoading}
              onClose={onClose}
              onSubmit={async (symbol) => {
                await onSubmit("CRYPTO", { symbol });
              }}
            />
          ) : modal.type === "quote" ? (
            <QuoteConfig
              modeId={modal.modeId}
              onClose={onClose}
              onSubmit={async (override) => {
                await onSubmit(modal.modeId, override);
              }}
            />
          ) : modal.type === "countdown" ? (
            <CountdownConfig
              onClose={onClose}
              onSubmit={async (override) => {
                await onSubmit("COUNTDOWN", override);
              }}
            />
          ) : modal.type === "habit" ? (
            <HabitConfig
              onClose={onClose}
              onSubmit={async (override) => {
                await onSubmit("HABIT", override);
              }}
            />
          ) : modal.type === "lifebar" ? (
            <LifebarConfig
              onClose={onClose}
              onSubmit={async (override) => {
                await onSubmit("LIFEBAR", override);
              }}
            />
          ) : modal.type === "webhook" ? (
            <WebhookConfig
              onClose={onClose}
              onSubmit={async (override) => {
                await onSubmit("WEBHOOK", override);
              }}
            />
          ) : modal.type === "pomodoro" ? (
            <PomodoroConfig
              locale={locale}
              onClose={onClose}
              onSubmit={async (override) => {
                await onSubmit("POMODORO", override);
              }}
            />
          ) : modal.type === "drink_water" ? (
            <DrinkWaterConfig
              locale={locale}
              onClose={onClose}
              onSubmit={async (override) => {
                await onSubmit("DRINK_WATER", override);
              }}
            />
          ) : modal.type === "server_status" ? (
            <ServerStatusConfig
              locale={locale}
              previewLoading={previewLoading}
              onClose={onClose}
              onSubmit={async (override) => {
                await onSubmit("SERVER_STATUS", override);
              }}
            />
          ) : (
            <div className="space-y-3">
              <p className="text-xs text-ink-light">
                {locale === "zh" ? "已就绪该组件快捷预览。" : "Ready for quick preview."}
              </p>
              <div className="pt-3 flex items-center justify-end gap-2 border-t border-ink/10">
                <Button variant="outline" size="sm" onClick={onClose}>
                  {locale === "zh" ? "关闭" : "Close"}
                </Button>
                <Button
                  size="sm"
                  onClick={async () => {
                    onClose();
                    await onSubmit(modal.modeId, {});
                  }}
                >
                  {locale === "zh" ? "刷新预览" : "Refresh Preview"}
                </Button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
