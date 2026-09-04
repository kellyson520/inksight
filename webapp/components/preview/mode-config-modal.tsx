"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Sliders, Star, BookmarkPlus, Check, Trash2, Plus } from "lucide-react";
import { LocationPicker } from "@/components/config/location-picker";
import { cleanLocationValue, type LocationValue } from "@/lib/locations";
import {
  HOTLIST_AVAILABLE_PLATFORMS,
  DISASTER_LEVELS,
  DISASTER_HAZARDS,
  POPULAR_STOCKS,
  POPULAR_CRYPTOS,
  SavedTickerItem,
  STORAGE_KEY_SAVED_TICKERS,
  STORAGE_KEY_DEFAULT_TICKER,
  DEFAULT_USER_SAVED_TICKERS,
} from "./types";

interface ModeConfigModalProps {
  modal: {
    type: "quote" | "weather" | "memo" | "countdown" | "habit" | "lifebar" | "calendar" | "timetable" | "rss" | "crypto" | "hotlist" | "disaster" | "webhook";
    modeId: string;
  };
  locale: string;
  previewLoading: boolean;
  onClose: () => void;
  onSubmit: (modeId: string, override: Record<string, unknown>) => Promise<void>;
  initialHotlistPlatforms: string[];
  initialDisasterLevel: string;
  initialDisasterHazard: string;
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
  initialDisasterLevel,
  initialDisasterHazard,
  initialRssFeedUrl,
  initialCryptoSymbol,
}: ModeConfigModalProps) {
  // 1. Hotlist
  const [hotlistPlatforms, setHotlistPlatforms] = useState<string[]>(initialHotlistPlatforms);

  // 2. Disaster Alert
  const [disasterLevel, setDisasterLevel] = useState<string>(initialDisasterLevel);
  const [disasterHazard, setDisasterHazard] = useState<string>(initialDisasterHazard);
  const [disasterCustomText, setDisasterCustomText] = useState<string>("");

  // 3. Weather
  const [weatherDraftLocation, setWeatherDraftLocation] = useState<LocationValue>({ city: "杭州" });

  // 4. Memo
  const [memoDraft, setMemoDraft] = useState({
    title1: "", text1: "",
    title2: "", text2: "",
    title3: "", text3: "",
  });

  // 5. Quote
  const [quoteDraft, setQuoteDraft] = useState("");
  const [authorDraft, setAuthorDraft] = useState("");

  // 6. RSS
  const [rssFeedUrl, setRssFeedUrl] = useState(initialRssFeedUrl);
  const [rssItemIndex, setRssItemIndex] = useState(0);
  const [rssShowImage, setRssShowImage] = useState(true);

  // 7. Crypto & Stocks
  const [cryptoSymbol, setCryptoSymbol] = useState(initialCryptoSymbol);
  const [savedTickers, setSavedTickers] = useState<SavedTickerItem[]>([]);
  const [defaultTicker, setDefaultTicker] = useState<string>("BTC");

  useEffect(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY_SAVED_TICKERS);
      if (saved) {
        const parsed = JSON.parse(saved);
        if (Array.isArray(parsed) && parsed.length > 0) {
          setSavedTickers(parsed);
        } else {
          setSavedTickers(DEFAULT_USER_SAVED_TICKERS);
        }
      } else {
        setSavedTickers(DEFAULT_USER_SAVED_TICKERS);
      }

      const def = localStorage.getItem(STORAGE_KEY_DEFAULT_TICKER);
      if (def) setDefaultTicker(def);
    } catch {
      setSavedTickers(DEFAULT_USER_SAVED_TICKERS);
    }
  }, []);

  const handleAddSavedTicker = (sym: string) => {
    const clean = sym.trim().toUpperCase();
    if (!clean) return;
    setSavedTickers((prev) => {
      if (prev.some((item) => item.sym === clean)) return prev;
      const foundStock = POPULAR_STOCKS.find((s) => s.sym === clean);
      const foundCrypto = POPULAR_CRYPTOS.find((c) => c.sym === clean);
      const name = foundStock ? foundStock.name : foundCrypto ? foundCrypto.name : undefined;
      const next = [...prev, { sym: clean, name, isCustom: true }];
      try {
        localStorage.setItem(STORAGE_KEY_SAVED_TICKERS, JSON.stringify(next));
      } catch {}
      return next;
    });
  };

  const handleRemoveSavedTicker = (sym: string, e?: React.MouseEvent) => {
    if (e) e.stopPropagation();
    setSavedTickers((prev) => {
      const next = prev.filter((item) => item.sym !== sym);
      try {
        localStorage.setItem(STORAGE_KEY_SAVED_TICKERS, JSON.stringify(next));
      } catch {}
      return next;
    });
  };

  const handleSetDefaultTicker = (sym: string, e?: React.MouseEvent) => {
    if (e) e.stopPropagation();
    const clean = sym.trim().toUpperCase();
    setDefaultTicker(clean);
    try {
      localStorage.setItem(STORAGE_KEY_DEFAULT_TICKER, clean);
    } catch {}
  };

  // 8. Countdown
  const [countdownName, setCountdownName] = useState("元旦");
  const [countdownDate, setCountdownDate] = useState("2027-01-01");

  // 9. Habit
  const [habitItems, setHabitItems] = useState([
    { name: "早起", done: false },
    { name: "运动", done: false },
    { name: "阅读", done: false },
  ]);

  // 10. Lifebar
  const [userAge, setUserAge] = useState(30);
  const [lifeExpectancy, setLifeExpectancy] = useState(80);

  // 11. Webhook
  const [webhookDraft, setWebhookDraft] = useState({
    title: "家庭环境与能耗",
    primary_metric: "24.5°C",
    primary_label: "舒适客厅温度",
    item_1_value: "52% 湿度适宜",
    item_2_value: "14 μg/m³ 优",
    item_3_value: "3.8 kWh 用电正常",
  });

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/45 backdrop-blur-2xs" onClick={onClose} />
      <div className="relative w-full max-w-lg rounded-sm border border-ink/20 bg-white shadow-2xl overflow-hidden">
        {/* Modal Header */}
        <div className="px-5 py-3.5 border-b border-ink/10 flex items-center justify-between bg-paper-dark">
          <div className="text-sm font-bold text-ink flex items-center gap-2">
            <Sliders size={16} />
            <span>
              {modal.type === "hotlist"
                ? (locale === "zh" ? "全网热点 · 多平台多选与聚合" : "Trending Topics Configuration")
                : modal.type === "disaster"
                ? (locale === "zh" ? "自然灾害预警 · 四级预警体验" : "Disaster Warning Alert Experience")
                : modal.type === "weather"
                ? (locale === "zh" ? "天气预报设置" : "Weather Settings")
                : modal.type === "memo"
                ? (locale === "zh" ? "便签内容设置" : "Memo Settings")
                : modal.type === "quote"
                ? (locale === "zh" ? "自定义语录设置" : "Quote Settings")
                : modal.type === "countdown"
                ? (locale === "zh" ? "倒计时设置" : "Countdown Settings")
                : modal.type === "habit"
                ? (locale === "zh" ? "习惯打卡项" : "Habit Tracker")
                : modal.type === "lifebar"
                ? (locale === "zh" ? "人生进度条" : "Life Progress")
                : modal.type === "rss"
                ? (locale === "zh" ? "RSS 订阅设置" : "RSS Settings")
                : modal.type === "crypto"
                ? (locale === "zh" ? "资产与股票行情设置" : "Stock & Asset Settings")
                : modal.type === "webhook"
                ? (locale === "zh" ? "开放数据卡片模拟" : "Webhook Card Simulator")
                : (locale === "zh" ? "模式参数设置" : "Mode Settings")}
            </span>
          </div>
          <button className="text-ink-light hover:text-ink text-sm p-1" onClick={onClose}>
            ✕
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-5 space-y-4 max-h-[75vh] overflow-y-auto">
          {/* 1. HOTLIST 全网热点平台多选 */}
          {modal.type === "hotlist" ? (
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
                    const isSelected = hotlistPlatforms.includes(p.id);
                    return (
                      <button
                        key={p.id}
                        type="button"
                        onClick={() => {
                          if (isSelected) {
                            if (hotlistPlatforms.length > 1) {
                              setHotlistPlatforms(hotlistPlatforms.filter((x) => x !== p.id));
                            }
                          } else {
                            setHotlistPlatforms([...hotlistPlatforms, p.id]);
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
                  onClick={() => setHotlistPlatforms(["zhihu", "weibo", "bilibili", "baidu", "github"])}
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
                      await onSubmit("HOTLIST", { platforms: hotlistPlatforms });
                    }}
                    disabled={previewLoading}
                    className="bg-ink text-white hover:bg-ink/90"
                  >
                    {locale === "zh" ? "应用并预览热点" : "Apply & Preview"}
                  </Button>
                </div>
              </div>
            </div>
          ) : modal.type === "disaster" ? (
            /* 2. DISASTER_ALERT 自然灾害预警体验与等级配置 */
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
                    await onSubmit("DISASTER_ALERT", {
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
          ) : modal.type === "weather" ? (
            /* 3. WEATHER 天气 */
            <div className="space-y-3">
              <div className="text-xs text-ink-light">
                {locale === "zh" ? "搜索并选择具体城市或地区：" : "Search and choose a specific location:"}
              </div>
              <LocationPicker
                value={weatherDraftLocation}
                onChange={setWeatherDraftLocation}
                locale={locale === "zh" ? "zh" : "en"}
                placeholder={locale === "zh" ? "输入城市名称（如：上海、北京、Tokyo）" : "Enter city name..."}
                className="w-full rounded-sm border border-ink/20 px-3 py-2 text-sm bg-white"
                autoFocus
              />
              <div className="pt-3 flex items-center justify-end gap-2 border-t border-ink/10">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setWeatherDraftLocation({ city: "杭州" })}
                >
                  {locale === "zh" ? "设为杭州" : "Reset"}
                </Button>
                <Button
                  size="sm"
                  onClick={async () => {
                    const loc = cleanLocationValue(weatherDraftLocation);
                    onClose();
                    await onSubmit("WEATHER", loc.city ? (loc as Record<string, unknown>) : {});
                  }}
                  disabled={previewLoading}
                >
                  {locale === "zh" ? "应用并预览" : "Apply"}
                </Button>
              </div>
            </div>
          ) : modal.type === "memo" ? (
            /* 4. MEMO 便签 */
            <div className="space-y-3">
              <div className="text-xs text-ink-light">
                {locale === "zh" ? "设置便签各栏位标题与内容：" : "Set memo contents:"}
              </div>
              {([1, 2, 3] as const).map((i) => {
                const tKey = `title${i}` as keyof typeof memoDraft;
                const cKey = `text${i}` as keyof typeof memoDraft;
                return (
                  <div key={i} className="space-y-1">
                    <input
                      value={memoDraft[tKey]}
                      onChange={(e) => setMemoDraft({ ...memoDraft, [tKey]: e.target.value })}
                      placeholder={locale === "zh" ? `标题 ${i}` : `Title ${i}`}
                      className="w-full rounded-sm border border-ink/20 px-2.5 py-1 text-xs bg-white font-medium"
                    />
                    <textarea
                      value={memoDraft[cKey]}
                      onChange={(e) => setMemoDraft({ ...memoDraft, [cKey]: e.target.value })}
                      placeholder={locale === "zh" ? `内容 ${i}` : `Text ${i}`}
                      rows={2}
                      className="w-full rounded-sm border border-ink/20 px-2.5 py-1 text-xs bg-white"
                    />
                  </div>
                );
              })}
              <div className="pt-3 flex items-center justify-end gap-2 border-t border-ink/10">
                <Button variant="outline" size="sm" onClick={onClose}>
                  {locale === "zh" ? "取消" : "Cancel"}
                </Button>
                <Button
                  size="sm"
                  onClick={async () => {
                    onClose();
                    await onSubmit("MEMO", {
                      memo_title_1: memoDraft.title1, memo_text_1: memoDraft.text1,
                      memo_title_2: memoDraft.title2, memo_text_2: memoDraft.text2,
                      memo_title_3: memoDraft.title3, memo_text_3: memoDraft.text3,
                    });
                  }}
                  disabled={previewLoading}
                >
                  {locale === "zh" ? "保存并预览" : "Apply"}
                </Button>
              </div>
            </div>
          ) : modal.type === "rss" ? (
            /* 5. RSS */
            <div className="space-y-3">
              <label className="text-xs font-semibold text-ink block">RSS 订阅地址：</label>
              <input
                value={rssFeedUrl}
                onChange={(e) => setRssFeedUrl(e.target.value)}
                className="w-full rounded-sm border border-ink/20 px-3 py-1.5 text-xs bg-white font-mono"
              />
              <div className="flex items-center gap-4 text-xs">
                <label className="flex items-center gap-1.5">
                  <input
                    type="checkbox"
                    checked={rssShowImage}
                    onChange={(e) => setRssShowImage(e.target.checked)}
                  />
                  <span>显示配图</span>
                </label>
                <label className="flex items-center gap-1.5">
                  <span>条目序号：</span>
                  <input
                    type="number"
                    min={0}
                    max={10}
                    value={rssItemIndex}
                    onChange={(e) => setRssItemIndex(Number(e.target.value))}
                    className="w-16 border rounded px-1.5 py-0.5"
                  />
                </label>
              </div>
              <div className="pt-3 flex items-center justify-end gap-2 border-t border-ink/10">
                <Button variant="outline" size="sm" onClick={onClose}>
                  取消
                </Button>
                <Button
                  size="sm"
                  onClick={async () => {
                    onClose();
                    await onSubmit("RSS", {
                      feed_url: rssFeedUrl,
                      item_index: rssItemIndex,
                      show_image: rssShowImage,
                    });
                  }}
                >
                  应用并预览
                </Button>
              </div>
            </div>
          ) : modal.type === "crypto" ? (
            /* 6. CRYPTO 资产与股票行情 */
            <div className="space-y-4">
              <div className="text-xs text-ink-light leading-relaxed">
                {locale === "zh"
                  ? "支持查阅与监控全球知名股票（美股/港股）与主流加密资产！支持将常用标的保存到自选列表或设为默认，方便下次一键调用。"
                  : "Track global stocks (Apple, Tesla, NVIDIA...) and major crypto assets. Save favorite tickers or set default for quick access next time."}
              </div>

              {/* 输入框与快捷加入自选 */}
              <div>
                <label className="text-xs font-semibold text-ink block mb-1.5">
                  {locale === "zh" ? "输入股票代码或加密代号" : "Enter Stock / Crypto Symbol"}
                </label>
                <div className="flex gap-2">
                  <input
                    value={cryptoSymbol}
                    onChange={(e) => setCryptoSymbol(e.target.value.toUpperCase())}
                    className="flex-1 rounded-sm border border-ink/20 px-3 py-1.5 text-xs bg-white font-mono uppercase font-semibold"
                    placeholder={locale === "zh" ? "例如 AAPL, TSLA, NVDA 或 BTC, ETH..." : "e.g. AAPL, TSLA, NVDA or BTC..."}
                  />
                  {cryptoSymbol.trim() ? (
                    <>
                      {savedTickers.some((t) => t.sym === cryptoSymbol.trim().toUpperCase()) ? (
                        <Button
                          variant={defaultTicker === cryptoSymbol.trim().toUpperCase() ? "default" : "outline"}
                          size="sm"
                          onClick={() => handleSetDefaultTicker(cryptoSymbol)}
                          className="text-xs px-2.5 flex items-center gap-1"
                          title={locale === "zh" ? "设为下次打开的默认标的" : "Set as default"}
                        >
                          <Star size={13} className={defaultTicker === cryptoSymbol.trim().toUpperCase() ? "fill-amber-400 text-amber-400" : ""} />
                          <span>{defaultTicker === cryptoSymbol.trim().toUpperCase() ? (locale === "zh" ? "当前默认" : "Default") : (locale === "zh" ? "设为默认" : "Set Default")}</span>
                        </Button>
                      ) : (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleAddSavedTicker(cryptoSymbol)}
                          className="text-xs px-2.5 flex items-center gap-1 bg-amber-50/50 border-amber-300 text-ink hover:bg-amber-100"
                        >
                          <BookmarkPlus size={13} className="text-amber-600" />
                          <span>{locale === "zh" ? "保存到自选" : "Save Ticker"}</span>
                        </Button>
                      )}
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setCryptoSymbol("")}
                        className="text-xs text-ink-light hover:text-ink px-2"
                      >
                        清空
                      </Button>
                    </>
                  ) : null}
                </div>
              </div>

              {/* 1. 用户已保存的自选资产专区 */}
              <div>
                <div className="text-xs font-semibold text-ink mb-1.5 flex items-center justify-between">
                  <div className="flex items-center gap-1.5">
                    <Star size={13} className="text-amber-500 fill-amber-500" />
                    <span>{locale === "zh" ? "我的常用自选标的 (已保存设置)" : "My Saved Tickers"}</span>
                  </div>
                  <span className="text-[11px] font-normal text-ink-light">
                    {locale === "zh" ? "点击直接切换 · 下次自动记住" : "Click to use · Auto remembered"}
                  </span>
                </div>
                {savedTickers.length > 0 ? (
                  <div className="flex flex-wrap gap-1.5 p-2 rounded-sm border border-dashed border-ink/20 bg-paper-light">
                    {savedTickers.map((item) => {
                      const isSelected = cryptoSymbol === item.sym;
                      const isDefault = defaultTicker === item.sym;
                      return (
                        <div
                          key={item.sym}
                          onClick={() => setCryptoSymbol(item.sym)}
                          className={`group flex items-center gap-1 px-2.5 py-1 rounded-sm border text-xs cursor-pointer transition-all ${
                            isSelected
                              ? "bg-ink text-white border-ink shadow-xs"
                              : "bg-white border-ink/15 text-ink hover:border-ink/50"
                          }`}
                        >
                          <span className="font-mono font-bold">{item.sym}</span>
                          {item.name ? (
                            <span className={`text-[10px] ${isSelected ? "text-white/80" : "text-ink-light"}`}>
                              {item.name}
                            </span>
                          ) : null}
                          {isDefault ? (
                            <Star size={10} className="fill-amber-400 text-amber-400 shrink-0" />
                          ) : null}
                          <button
                            type="button"
                            onClick={(e) => handleRemoveSavedTicker(item.sym, e)}
                            className={`ml-1 text-[10px] p-0.5 rounded-xs transition-colors ${
                              isSelected
                                ? "text-white/60 hover:text-white hover:bg-white/20"
                                : "text-ink-light hover:text-red-600 hover:bg-red-50"
                            }`}
                            title={locale === "zh" ? "从自选移除" : "Remove"}
                          >
                            ✕
                          </button>
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <div className="text-[11px] text-ink-light p-2 border border-dashed border-ink/20 rounded-sm bg-paper-light text-center">
                    {locale === "zh" ? "暂无自选标的，输入代码后点击【保存到自选】即可快速收纳。" : "No saved tickers yet. Enter a symbol and click 'Save Ticker'."}
                  </div>
                )}
              </div>

              {/* 2. 热门全球股票专区 */}
              <div>
                <div className="text-xs font-semibold text-ink mb-1.5 flex items-center justify-between">
                  <span>{locale === "zh" ? "热门股票标的 (美股/港股)" : "Popular Global Stocks"}</span>
                  <span className="text-[11px] font-normal text-ink-light">
                    {locale === "zh" ? "点击一键选择" : "Click to select"}
                  </span>
                </div>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-1.5">
                  {POPULAR_STOCKS.map((stk) => {
                    const isSelected = cryptoSymbol === stk.sym;
                    return (
                      <button
                        key={stk.sym}
                        type="button"
                        onClick={() => setCryptoSymbol(stk.sym)}
                        className={`px-2.5 py-1.5 rounded-sm border text-left transition-all ${
                          isSelected
                            ? "bg-ink text-white border-ink shadow-xs"
                            : "bg-paper-light border-ink/15 text-ink hover:border-ink/50 hover:bg-white"
                        }`}
                      >
                        <div className="text-xs font-bold font-mono leading-tight">{stk.sym}</div>
                        <div className={`text-[10px] truncate ${isSelected ? "text-white/80" : "text-ink-light"}`}>
                          {locale === "zh" ? stk.name : stk.desc}
                        </div>
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* 3. 热门加密资产专区 */}
              <div>
                <div className="text-xs font-semibold text-ink mb-1.5">
                  {locale === "zh" ? "热门加密资产" : "Popular Crypto Assets"}
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {POPULAR_CRYPTOS.map((c) => {
                    const isSelected = cryptoSymbol === c.sym;
                    return (
                      <button
                        key={c.sym}
                        type="button"
                        onClick={() => setCryptoSymbol(c.sym)}
                        className={`px-3 py-1 rounded-sm border text-xs font-mono transition-all ${
                          isSelected
                            ? "bg-ink text-white border-ink shadow-xs"
                            : "bg-paper-light border-ink/15 text-ink hover:border-ink/50 hover:bg-white"
                        }`}
                      >
                        <span className="font-bold">{c.sym}</span>
                        {locale === "zh" ? <span className="ml-1 text-[11px] opacity-75">{c.name}</span> : null}
                      </button>
                    );
                  })}
                </div>
              </div>

              <div className="pt-3 flex items-center justify-between gap-2 border-t border-ink/10">
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setCryptoSymbol("AAPL")}
                    className="text-xs text-ink-light"
                  >
                    {locale === "zh" ? "股票示例 (AAPL)" : "Stock Demo"}
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setCryptoSymbol("BTC")}
                    className="text-xs text-ink-light"
                  >
                    {locale === "zh" ? "默认 (BTC)" : "Default (BTC)"}
                  </Button>
                </div>
                <div className="flex items-center gap-2">
                  <Button variant="outline" size="sm" onClick={onClose}>
                    取消
                  </Button>
                  <Button
                    size="sm"
                    disabled={previewLoading || !cryptoSymbol.trim()}
                    onClick={async () => {
                      const targetSym = cryptoSymbol.trim().toUpperCase() || "BTC";
                      // 自动保存到最近使用和默认存储
                      try {
                        localStorage.setItem(STORAGE_KEY_DEFAULT_TICKER, targetSym);
                      } catch {}
                      onClose();
                      await onSubmit("CRYPTO", { symbol: targetSym });
                    }}
                  >
                    {locale === "zh" ? "保存并预览" : "Save & Preview"}
                  </Button>
                </div>
              </div>
            </div>
          ) : modal.type === "quote" ? (
            /* 7. QUOTE 语录 */
            <div className="space-y-3">
              <textarea
                value={quoteDraft}
                onChange={(e) => setQuoteDraft(e.target.value)}
                placeholder="输入自定义名言箴言..."
                className="w-full rounded-sm border border-ink/20 px-3 py-2 text-sm min-h-24 bg-white"
              />
              <input
                value={authorDraft}
                onChange={(e) => setAuthorDraft(e.target.value)}
                placeholder="作者（选填）"
                className="w-full rounded-sm border border-ink/20 px-3 py-1.5 text-xs bg-white"
              />
              <div className="pt-3 flex items-center justify-end gap-2 border-t border-ink/10">
                <Button variant="outline" size="sm" onClick={onClose}>
                  取消
                </Button>
                <Button
                  size="sm"
                  onClick={async () => {
                    onClose();
                    await onSubmit(modal.modeId, quoteDraft.trim() ? { quote: quoteDraft.trim(), author: authorDraft.trim() } : {});
                  }}
                >
                  保存并预览
                </Button>
              </div>
            </div>
          ) : modal.type === "countdown" ? (
            /* 8. COUNTDOWN 倒计时 */
            <div className="space-y-3">
              <input
                value={countdownName}
                onChange={(e) => setCountdownName(e.target.value)}
                placeholder="目标事件名称（如：高考、跨年）"
                className="w-full rounded-sm border border-ink/20 px-3 py-1.5 text-xs bg-white"
              />
              <input
                type="date"
                value={countdownDate}
                onChange={(e) => setCountdownDate(e.target.value)}
                className="w-full rounded-sm border border-ink/20 px-3 py-1.5 text-xs bg-white"
              />
              <div className="pt-3 flex items-center justify-end gap-2 border-t border-ink/10">
                <Button variant="outline" size="sm" onClick={onClose}>
                  取消
                </Button>
                <Button
                  size="sm"
                  onClick={async () => {
                    onClose();
                    await onSubmit("COUNTDOWN", {
                      countdown_events: [{ name: countdownName, date: countdownDate, type: "countdown" }],
                    });
                  }}
                >
                  应用并预览
                </Button>
              </div>
            </div>
          ) : modal.type === "habit" ? (
            /* 9. HABIT 习惯打卡 */
            <div className="space-y-3">
              {habitItems.map((item, idx) => (
                <div key={idx} className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={item.done}
                    onChange={(e) => {
                      const copy = [...habitItems];
                      copy[idx].done = e.target.checked;
                      setHabitItems(copy);
                    }}
                  />
                  <input
                    value={item.name}
                    onChange={(e) => {
                      const copy = [...habitItems];
                      copy[idx].name = e.target.value;
                      setHabitItems(copy);
                    }}
                    className="flex-1 rounded-sm border border-ink/20 px-2 py-1 text-xs"
                  />
                </div>
              ))}
              <div className="pt-3 flex items-center justify-end gap-2 border-t border-ink/10">
                <Button variant="outline" size="sm" onClick={onClose}>
                  取消
                </Button>
                <Button
                  size="sm"
                  onClick={async () => {
                    onClose();
                    await onSubmit("HABIT", { habits: habitItems });
                  }}
                >
                  应用并预览
                </Button>
              </div>
            </div>
          ) : modal.type === "lifebar" ? (
            /* 10. LIFEBAR 人生进度条 */
            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="text-xs text-ink block mb-1">当前年龄：</label>
                  <input
                    type="number"
                    min={1}
                    max={120}
                    value={userAge}
                    onChange={(e) => setUserAge(Number(e.target.value))}
                    className="w-full rounded-sm border border-ink/20 px-2 py-1 text-xs"
                  />
                </div>
                <div>
                  <label className="text-xs text-ink block mb-1">预期寿命：</label>
                  <input
                    type="number"
                    min={40}
                    max={150}
                    value={lifeExpectancy}
                    onChange={(e) => setLifeExpectancy(Number(e.target.value))}
                    className="w-full rounded-sm border border-ink/20 px-2 py-1 text-xs"
                  />
                </div>
              </div>
              <div className="pt-3 flex items-center justify-end gap-2 border-t border-ink/10">
                <Button variant="outline" size="sm" onClick={onClose}>
                  取消
                </Button>
                <Button
                  size="sm"
                  onClick={async () => {
                    onClose();
                    await onSubmit("LIFEBAR", { user_age: userAge, life_expectancy: lifeExpectancy });
                  }}
                >
                  应用并预览
                </Button>
              </div>
            </div>
          ) : modal.type === "webhook" ? (
            /* 11. WEBHOOK 模拟数据 */
            <div className="space-y-2.5">
              <input
                value={webhookDraft.title}
                onChange={(e) => setWebhookDraft({ ...webhookDraft, title: e.target.value })}
                placeholder="卡片标题"
                className="w-full rounded-sm border border-ink/20 px-2.5 py-1 text-xs"
              />
              <div className="grid grid-cols-2 gap-2">
                <input
                  value={webhookDraft.primary_metric}
                  onChange={(e) => setWebhookDraft({ ...webhookDraft, primary_metric: e.target.value })}
                  placeholder="主指标数值"
                  className="w-full rounded-sm border border-ink/20 px-2.5 py-1 text-xs font-mono"
                />
                <input
                  value={webhookDraft.primary_label}
                  onChange={(e) => setWebhookDraft({ ...webhookDraft, primary_label: e.target.value })}
                  placeholder="主指标说明"
                  className="w-full rounded-sm border border-ink/20 px-2.5 py-1 text-xs"
                />
              </div>
              <div className="pt-3 flex items-center justify-end gap-2 border-t border-ink/10">
                <Button variant="outline" size="sm" onClick={onClose}>
                  取消
                </Button>
                <Button
                  size="sm"
                  onClick={async () => {
                    onClose();
                    await onSubmit("WEBHOOK", webhookDraft);
                  }}
                >
                  模拟并预览
                </Button>
              </div>
            </div>
          ) : (
            /* 通用兜底 */
            <div className="space-y-3">
              <p className="text-xs text-ink-light">已就绪该组件快捷预览。</p>
              <div className="pt-3 flex items-center justify-end gap-2 border-t border-ink/10">
                <Button variant="outline" size="sm" onClick={onClose}>
                  关闭
                </Button>
                <Button
                  size="sm"
                  onClick={async () => {
                    onClose();
                    await onSubmit(modal.modeId, {});
                  }}
                >
                  刷新预览
                </Button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
