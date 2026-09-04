"use client";

import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import Image from "next/image";
import { usePathname, useRouter } from "next/navigation";
import { LocationPicker } from "@/components/config/location-picker";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  AlertCircle,
  Eye,
  Loader2,
  Plus,
  Settings,
  ChevronLeft,
  ChevronRight,
  RefreshCw,
  Sparkles,
  Layers,
  Heart,
  Briefcase,
  Newspaper,
  Sliders,
  Check,
  Flame,
  AlertTriangle,
  Download,
  Search,
} from "lucide-react";
import { localeFromPathname, t, withLocalePath } from "@/lib/i18n";
import { cleanLocationValue, type LocationValue } from "@/lib/locations";
import { authHeaders, fetchCurrentUser } from "@/lib/auth";
import { ColorSelect } from "@/components/ui/color-select";
import { ScreenSizeSelect } from "@/components/ui/screen-size-select";
import { CalendarReminders } from "@/components/config/calendar-reminders";
import { TimetableEditor, type TimetableData } from "@/components/config/timetable-editor";

type ModeCatalogItem = {
  mode_id: string;
  category: "core" | "more" | "custom" | string;
  source?: string;
  display_name?: string;
  description?: string;
  i18n?: {
    zh?: { name?: string; tip?: string };
    en?: { name?: string; tip?: string };
  };
};

type PrimaryCategory = "all" | "life" | "productivity" | "news";

// 模式到【生活 / 效率 / 资讯】一级分类的权威映射
const MODE_PRIMARY_CATEGORY: Record<string, "life" | "productivity" | "news"> = {
  // 生活 (Life)
  DAILY: "life",
  WEATHER: "life",
  ZEN: "life",
  POETRY: "life",
  ARTWALL: "life",
  ALMANAC: "life",
  RECIPE: "life",
  ROAST: "life",
  FITNESS: "life",
  LETTER: "life",
  RIDDLE: "life",
  QUESTION: "life",
  STORY: "life",
  MY_QUOTE: "life",
  MY_ADAPTIVE: "life",

  // 效率 (Productivity)
  COUNTDOWN: "productivity",
  MEMO: "productivity",
  HABIT: "productivity",
  LIFEBAR: "productivity",
  CALENDAR: "productivity",
  TIMETABLE: "productivity",
  CHALLENGE: "productivity",
  WORD_OF_THE_DAY: "productivity",
  WEBHOOK: "productivity",

  // 资讯 (News & Alerts)
  BRIEFING: "news",
  HOTLIST: "news",
  MOYU: "news",
  RSS: "news",
  CRYPTO: "news",
  THISDAY: "news",
  BIAS: "news",
  DISASTER_ALERT: "news",
};

const CONFIGURABLE_MODES: Record<string, string> = {
  HOTLIST: "hotlist",
  DISASTER_ALERT: "disaster",
  WEATHER: "weather",
  MEMO: "memo",
  MY_QUOTE: "quote",
  COUNTDOWN: "countdown",
  HABIT: "habit",
  LIFEBAR: "lifebar",
  CALENDAR: "calendar",
  TIMETABLE: "timetable",
  RSS: "rss",
  CRYPTO: "crypto",
  WEBHOOK: "webhook",
  MY_ADAPTIVE: "adaptive",
};

const HOTLIST_AVAILABLE_PLATFORMS = [
  { id: "zhihu", label: "知乎热榜", desc: "高热深度讨论" },
  { id: "weibo", label: "微博热搜", desc: "全民实时热度" },
  { id: "bilibili", label: "B站热门", desc: "热门视频与科技" },
  { id: "baidu", label: "百度热搜", desc: "全网即时事件" },
  { id: "github", label: "GitHub Trending", desc: "全球开源热门趋势" },
];

const DISASTER_LEVELS = [
  { id: "红色", roman: "I级", label: "红色预警", desc: "特别严重 · 最高警戒", color: "text-red-600 border-red-300 bg-red-50" },
  { id: "橙色", roman: "II级", label: "橙色预警", desc: "严重 · 紧急防范", color: "text-orange-600 border-orange-300 bg-orange-50" },
  { id: "黄色", roman: "III级", label: "黄色预警", desc: "较重 · 密切防灾", color: "text-amber-600 border-amber-300 bg-amber-50" },
  { id: "蓝色", roman: "IV级", label: "蓝色预警", desc: "一般 · 注意避险", color: "text-blue-600 border-blue-300 bg-blue-50" },
];

const DISASTER_HAZARDS = [
  { id: "暴雨", label: "暴雨 / 洪涝" },
  { id: "台风", label: "台风 / 强风暴" },
  { id: "暴雪", label: "暴雪 / 结冰" },
  { id: "大风", label: "大风 / 强对流" },
  { id: "高温", label: "高温 / 酷热" },
  { id: "寒潮", label: "寒潮 / 霜冻" },
  { id: "地震", label: "地震 / 地质灾害" },
  { id: "森林火险", label: "森林火险" },
  { id: "海啸", label: "海啸" },
  { id: "冰雹", label: "冰雹" },
  { id: "沙尘暴", label: "沙尘暴" },
  { id: "大雾", label: "大雾 / 雾霾" },
];

/**
 * 分页式模式容器组件：支持上一页/下一页、页码指示、即点即显
 */
function PaginatedModeSection({
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
}: {
  title: string;
  subtitle?: string;
  icon?: typeof Sparkles;
  modes: string[];
  currentMode: string;
  onPreview: (m: string) => void;
  onConfigure: (m: string) => void;
  customMeta?: Record<string, { name: string; tip: string; category?: string }>;
  tailItem?: ReactNode;
  locale: string;
  pageSize?: number;
}) {
  const [page, setPage] = useState(0);

  // 当外部筛选变更导致页码越界时重置
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
  const showTailHere = tailItem && startIndex + visibleModes.length <= totalSlots && startIndex + visibleModes.length >= modes.length;

  return (
    <div className="mb-6 rounded-sm border border-ink/10 bg-white/60 p-4 shadow-sm backdrop-blur-xs">
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
                  ? "border-ink bg-paper-dark shadow-sm ring-1 ring-ink"
                  : "border-ink/15 bg-white hover:border-ink/40 hover:bg-paper-light"
              }`}
            >
              {/* 卡片主体：点击即展示 */}
              <button
                onClick={() => onPreview(m)}
                className="w-full p-2.5 text-left flex-1 flex flex-col justify-start"
              >
                <div className="flex items-center justify-between gap-1 w-full mb-1">
                  <span className={`text-xs font-bold truncate ${isCurrent ? "text-ink" : "text-ink"}`}>
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
              <div className="border-t border-ink/10 bg-white/70 px-2 py-1 flex items-center justify-between gap-1">
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

export default function ExperiencePage() {
  const router = useRouter();
  const pathname = usePathname();
  const locale = localeFromPathname(pathname || "/");

  const [authChecked, setAuthChecked] = useState(false);
  const [userLlmApiKey, setUserLlmApiKey] = useState<string>("");

  const [catalogItems, setCatalogItems] = useState<ModeCatalogItem[]>([]);
  const [modesError, setModesError] = useState<string | null>(null);

  // 默认启动模式（优先全网热点或天气）
  const [previewMode, setPreviewMode] = useState("HOTLIST");
  const [previewColors, setPreviewColors] = useState(3);
  const [previewWidth, setPreviewWidth] = useState(400);
  const [previewHeight, setPreviewHeight] = useState(300);
  const [previewModeNameOverride, setPreviewModeNameOverride] = useState<string | null>(null);

  // 一级分类标签：全部 / 生活 / 效率 / 资讯
  const [primaryTab, setPrimaryTab] = useState<PrimaryCategory>("all");
  const [searchKeyword, setSearchKeyword] = useState<string>("");

  const [city] = useState("杭州");
  const [memoText] = useState(t(locale, "preview.memo.default", "写点什么吧…"));
  const defaultMemoDraft = { title1: "", text1: "", title2: "", text2: "", title3: "", text3: "" };

  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState<string | null>(null);
  const [toast, setToast] = useState<{ msg: string; type: "success" | "error" | "info" } | null>(null);

  const [previewLlmStatus, setPreviewLlmStatus] = useState<string | null>(null);
  const [previewImageUrl, setPreviewImageUrl] = useState<string | null>(null);
  const lastObjectUrlRef = useRef<string | null>(null);
  const toastTimerRef = useRef<number | null>(null);

  // 快捷参数调节模态窗
  const [modal, setModal] = useState<null | {
    type: "quote" | "weather" | "memo" | "countdown" | "habit" | "lifebar" | "calendar" | "timetable" | "rss" | "crypto" | "hotlist" | "disaster" | "webhook";
    modeId: string;
  }>(null);

  const [_imageUploadLoading, setImageUploadLoading] = useState(false);
  const [quoteDraft, setQuoteDraft] = useState("");
  const [authorDraft, setAuthorDraft] = useState("");
  const [weatherDraftLocation, setWeatherDraftLocation] = useState<LocationValue>({ city: "杭州" });
  const [memoDraft, setMemoDraft] = useState<{ title1: string; text1: string; title2: string; text2: string; title3: string; text3: string }>({
    title1: "", text1: "", title2: "", text2: "", title3: "", text3: "",
  });
  const [rssFeedUrl, setRssFeedUrl] = useState("https://kellson.dpdns.org:81/playno1/av");
  const [rssItemIndex, setRssItemIndex] = useState(0);
  const [rssShowImage, setRssShowImage] = useState(true);
  const [cryptoSymbol, setCryptoSymbol] = useState("BTC");

  // 全网热点平台多选状态（支持多选聚合！）
  const [hotlistPlatforms, setHotlistPlatforms] = useState<string[]>(["zhihu", "weibo"]);

  // 自然灾害预警配置状态
  const [disasterLevel, setDisasterLevel] = useState<string>("红色");
  const [disasterHazard, setDisasterHazard] = useState<string>("暴雨");
  const [disasterCustomText, setDisasterCustomText] = useState<string>("");

  const [webhookDraft, setWebhookDraft] = useState({
    title: "家庭环境与能耗",
    primary_metric: "24.5°C",
    primary_label: "舒适客厅温度",
    item_1_value: "52% 湿度适宜",
    item_2_value: "14 μg/m³ 优",
    item_3_value: "3.8 kWh 用电正常",
  });
  const [calendarReminders, setCalendarReminders] = useState<Record<string, string>>({});
  const [timetableData, setTimetableData] = useState<TimetableData>({
    style: "weekly",
    periods: ["08:00-09:30", "10:00-11:30", "14:00-15:30", "16:00-17:30"],
    courses: {
      "0-0": "高等数学/A201", "0-2": "线性代数/A201",
      "1-1": "大学英语/B305", "1-3": "体育/操场",
      "2-0": "数据结构/C102", "2-2": "计算机网络/C102",
      "3-1": "概率论/A201", "3-3": "毛概/D405",
      "4-0": "操作系统/C102",
    },
  });

  const [countdownName, setCountdownName] = useState("元旦");
  const [countdownDate, setCountdownDate] = useState("2027-01-01");

  const [habitItems, setHabitItems] = useState([
    { name: "早起", done: false },
    { name: "运动", done: false },
    { name: "阅读", done: false },
  ]);

  const [userAge, setUserAge] = useState(30);
  const [lifeExpectancy, setLifeExpectancy] = useState(80);

  const [showCustomModeModal, setShowCustomModeModal] = useState(false);
  const [customDesc, setCustomDesc] = useState("");
  const [customModeName, setCustomModeName] = useState("");
  const [customJson, setCustomJson] = useState("");
  const [customGenerating, setCustomGenerating] = useState(false);

  const adaptiveFileInputRef = useRef<HTMLInputElement | null>(null);

  const uploadLocalImage = async (file: File): Promise<string> => {
    const fd = new FormData();
    fd.append("file", file);
    const up = await fetch("/api/uploads", { method: "POST", body: fd });
    if (!up.ok) {
      const err = await up.text().catch(() => "");
      throw new Error(err || `upload failed: ${up.status}`);
    }
    const data = (await up.json()) as { url?: string };
    if (!data.url) throw new Error("upload failed: missing url");
    return data.url;
  };

  // 身份检查
  useEffect(() => {
    fetchCurrentUser()
      .then((u) => {
        if (!u) {
          router.replace(withLocalePath(locale, "/login"));
          return;
        }
        setAuthChecked(true);
      })
      .catch(() => {
        router.replace(withLocalePath(locale, "/login"));
      });
  }, [locale, router]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const k = localStorage.getItem("ink_user_llm_api_key") || "";
    if (k.trim()) setUserLlmApiKey(k.trim());
  }, []);

  const [showInviteModal, setShowInviteModal] = useState(false);
  const [inviteCode, setInviteCode] = useState("");
  const [redeemingInvite, setRedeemingInvite] = useState(false);
  const [pendingPreviewMode, setPendingPreviewMode] = useState<string | null>(null);

  const showToast = (msg: string, type: "success" | "error" | "info" = "info") => {
    setToast({ msg, type });
    if (toastTimerRef.current) window.clearTimeout(toastTimerRef.current);
    toastTimerRef.current = window.setTimeout(() => setToast(null), 2500);
  };

  // 模式元数据构建
  const modeMeta = useMemo(() => {
    const map: Record<string, { name: string; tip: string; category?: string }> = {};
    for (const item of catalogItems) {
      const mid = (item.mode_id || "").toUpperCase();
      if (!mid) continue;
      const lang = locale === "en" ? item.i18n?.en : item.i18n?.zh;
      const name =
        (lang?.name && String(lang.name)) ||
        (item.display_name && String(item.display_name)) ||
        mid;
      const tip =
        (lang?.tip && String(lang.tip)) ||
        (item.description && String(item.description)) ||
        "";
      map[mid] = { name, tip, category: item.category };
    }
    return map;
  }, [catalogItems, locale]);

  // 根据一级分类与关键词过滤模式
  const filteredModes = useMemo(() => {
    return catalogItems.filter((item) => {
      const mid = item.mode_id.toUpperCase();
      // 1. 一级分类匹配
      if (primaryTab !== "all") {
        const prim = MODE_PRIMARY_CATEGORY[mid] || (item.category === "custom" ? "productivity" : "life");
        if (prim !== primaryTab) return false;
      }
      // 2. 关键词匹配
      if (searchKeyword.trim()) {
        const kw = searchKeyword.trim().toLowerCase();
        const meta = modeMeta[mid];
        const matchId = mid.toLowerCase().includes(kw);
        const matchName = meta?.name.toLowerCase().includes(kw);
        const matchTip = meta?.tip.toLowerCase().includes(kw);
        if (!matchId && !matchName && !matchTip) return false;
      }
      return true;
    });
  }, [catalogItems, primaryTab, searchKeyword, modeMeta]);

  // 拆分二级子类
  const coreModes = useMemo(
    () => filteredModes.filter((m) => m.category === "core").map((m) => m.mode_id.toUpperCase()),
    [filteredModes],
  );
  const moreModes = useMemo(
    () => filteredModes.filter((m) => m.category === "more").map((m) => m.mode_id.toUpperCase()),
    [filteredModes],
  );
  const customModes = useMemo(
    () => filteredModes.filter((m) => m.category === "custom").map((m) => m.mode_id.toUpperCase()),
    [filteredModes],
  );

  const previewModeName =
    previewModeNameOverride ||
    modeMeta[previewMode]?.name ||
    previewMode ||
    t(locale, "preview.unknown_mode", "Unknown");

  /**
   * 核心预览请求处理器：全面支持直接点击模式即显与覆盖参数
   */
  const handlePreview = async (modeId?: string, override?: Record<string, unknown> | LocationValue) => {
    const targetMode = modeId || previewMode;
    if (!targetMode) return;
    if (!authChecked) return;

    setPreviewLlmStatus(null);
    setPreviewLoading(true);
    setPreviewError(null);

    try {
      const params = new URLSearchParams();
      params.set("persona", targetMode);
      params.set("ui_language", locale === "en" ? "en" : "zh");
      if (previewColors > 2) params.set("colors", String(previewColors));
      params.set("w", String(previewWidth));
      params.set("h", String(previewHeight));

      // 城市覆盖
      const cityOverride = override?.city ? String(override.city) : city.trim();
      if (cityOverride) {
        params.set("city_override", cityOverride);
      }

      // 便签
      if (targetMode === "MEMO" && override) {
        for (const i of [1, 2, 3]) {
          const tk = `memo_title_${i}`;
          const ck = `memo_text_${i}`;
          if (tk in override) params.set(tk, String((override as Record<string, unknown>)[tk]));
          if (ck in override) params.set(ck, String((override as Record<string, unknown>)[ck]));
        }
      }

      const mergedOverride: Record<string, unknown> = { ...(override || {}) };

      // 针对全网热点：自动附加当前多选平台
      if (targetMode === "HOTLIST" && !mergedOverride.platforms && !mergedOverride.platform) {
        mergedOverride.platforms = hotlistPlatforms;
      }

      // 针对自然灾害预警：自动附加当前预警级别与灾害类型
      if (targetMode === "DISASTER_ALERT") {
        if (!mergedOverride.level) mergedOverride.level = disasterLevel;
        if (!mergedOverride.hazard) mergedOverride.hazard = disasterHazard;
        if (disasterCustomText.trim()) mergedOverride.text = disasterCustomText.trim();
      }

      if (targetMode.toUpperCase() === "CALENDAR" && Object.keys(calendarReminders).length > 0) {
        mergedOverride.reminders = calendarReminders;
      }
      if (targetMode.toUpperCase() === "TIMETABLE" && !override) {
        mergedOverride.style = timetableData.style;
        mergedOverride.weekdays = timetableData.weekdays;
        mergedOverride.periods = timetableData.periods;
        mergedOverride.courses = timetableData.courses;
      }
      if (Object.keys(mergedOverride).length > 0) {
        params.set("mode_override", JSON.stringify(mergedOverride));
      }

      const res = await fetch(`/api/preview?${params.toString()}`, {
        headers: authHeaders(userLlmApiKey ? { "x-inksight-llm-api-key": userLlmApiKey } : undefined),
      });

      if (res.status === 402) {
        const data = await res.json().catch(() => ({}));
        if (data.requires_invite_code) {
          setPendingPreviewMode(targetMode);
          setShowInviteModal(true);
          setPreviewLoading(false);
          return;
        }
      }
      if (!res.ok) {
        const errText = await res.text().catch(() => "Unknown error");
        throw new Error(`${t(locale, "preview.error.preview_failed", "Preview failed")}: HTTP ${res.status} ${errText.substring(0, 120)}`);
      }

      const statusHeader = res.headers.get("x-preview-status");
      const llmRequired = res.headers.get("x-llm-required");
      const modeName = targetMode || "";

      if (statusHeader === "no_llm_required" || llmRequired === "0") {
        setPreviewLlmStatus(null);
      } else if (statusHeader === "static_served") {
        if (modeName === "POETRY") {
          setPreviewLlmStatus(locale === "zh" ? "古诗词已加载" : "Served from static poetry");
        } else if (modeName === "THISDAY") {
          setPreviewLlmStatus(locale === "zh" ? "历史今日已加载" : "Served from static history");
        } else if (modeName === "RIDDLE") {
          setPreviewLlmStatus(locale === "zh" ? "每日一谜已加载" : "Served from static riddles");
        } else {
          setPreviewLlmStatus(locale === "zh" ? "静态内容已加载" : "Static content served");
        }
      } else if (statusHeader === "model_generated") {
        setPreviewLlmStatus(locale === "zh" ? "大模型调用成功" : "Model call succeeded");
      } else if (statusHeader === "fallback_used") {
        setPreviewLlmStatus(locale === "zh" ? "大模型调用失败，使用默认内容" : "Model call failed, using fallback content");
      } else {
        setPreviewLlmStatus(null);
      }

      const blob = await res.blob();
      const objectUrl = URL.createObjectURL(blob);
      if (lastObjectUrlRef.current) URL.revokeObjectURL(lastObjectUrlRef.current);
      lastObjectUrlRef.current = objectUrl;
      setPreviewImageUrl(objectUrl);
      showToast(t(locale, "preview.toast.updated", "Preview updated"), "success");
    } catch (err) {
      const msg = err instanceof Error ? err.message : t(locale, "preview.error.preview_failed", "Preview failed");
      setPreviewError(msg);
      showToast(msg, "error");
    } finally {
      setPreviewLoading(false);
    }
  };

  /**
   * 点击模式卡片：即点即显
   */
  const handleModeCardClick = async (modeId: string) => {
    setPreviewMode(modeId);
    setPreviewModeNameOverride(null);

    if (modeId === "MY_ADAPTIVE") {
      adaptiveFileInputRef.current?.click();
      return;
    }

    await handlePreview(modeId);
  };

  /**
   * 点击配置按钮：打开对应的参数调节窗口
   */
  const handleOpenConfigModal = (modeId: string) => {
    setPreviewMode(modeId);
    const cfgType = CONFIGURABLE_MODES[modeId];
    if (cfgType) {
      setModal({ type: cfgType as never, modeId });
    }
  };

  const handleCustomModePreview = async (defOverride?: unknown) => {
    if (!defOverride && !customJson.trim()) return;
    setPreviewLoading(true);
    setPreviewError(null);
    try {
      const modeDef = defOverride || JSON.parse(customJson);
      const res = await fetch("/api/modes/custom/preview", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          mode_def: modeDef,
          screen_w: previewWidth,
          screen_h: previewHeight,
          colors: previewColors,
        }),
      });
      if (!res.ok) {
        const errText = await res.text().catch(() => "Unknown error");
        throw new Error(`HTTP ${res.status}: ${errText.substring(0, 100)}`);
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      if (lastObjectUrlRef.current) URL.revokeObjectURL(lastObjectUrlRef.current);
      lastObjectUrlRef.current = url;
      setPreviewImageUrl(url);
      setPreviewMode((modeDef as { mode_id?: string })?.mode_id?.toUpperCase() || "CUSTOM");
      setPreviewModeNameOverride((modeDef as { display_name?: string })?.display_name || "自定义模式");
      showToast(t(locale, "preview.toast.updated", "Preview updated"), "success");
    } catch (e) {
      const msg = (locale === "zh" ? "自定义模式预览失败: " : "Custom mode failed: ") + (e instanceof Error ? e.message : "Unknown error");
      setPreviewError(msg);
      showToast(msg, "error");
    } finally {
      setPreviewLoading(false);
    }
  };

  const handleGenerateCustomModeAndPreview = async () => {
    if (!customDesc.trim()) {
      showToast(locale === "zh" ? "请输入模式描述" : "Please enter a description for the mode", "error");
      return;
    }
    setCustomGenerating(true);
    try {
      const res = await fetch("/api/modes/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ description: customDesc }),
      });
      const data = await res.json();
      if (!data.ok) throw new Error(data.error || "Generate failed");
      setCustomJson(JSON.stringify(data.mode_def, null, 2));
      if (!customModeName.trim()) {
        setCustomModeName((data.mode_def?.display_name || "").toString());
      }
      setShowCustomModeModal(false);
      await handleCustomModePreview(data.mode_def);
    } catch (e) {
      showToast((locale === "zh" ? "生成失败: " : "Generate failed: ") + (e instanceof Error ? e.message : "Unknown error"), "error");
    } finally {
      setCustomGenerating(false);
    }
  };

  // 加载目录数据
  useEffect(() => {
    setModesError(null);
    if (!authChecked) return;
    fetch("/api/modes/catalog", { headers: authHeaders() })
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((d) => {
        if (d.items && Array.isArray(d.items)) {
          setCatalogItems(d.items);
        } else {
          setModesError(t(locale, "preview.error.no_modes", "No modes data"));
        }
      })
      .catch((e) => {
        setModesError(`${t(locale, "preview.error.load_failed", "Failed to load modes")}: ${e.message}`);
      });
  }, [authChecked, locale]);

  // 初始自动生成全网热点预览
  useEffect(() => {
    if (authChecked && catalogItems.length > 0 && !previewImageUrl && !previewLoading) {
      handlePreview("HOTLIST", { platforms: hotlistPlatforms });
    }
  }, [authChecked, catalogItems.length]);

  return (
    <div className="mx-auto max-w-7xl px-4 sm:px-6 py-6 sm:py-10">
      {/* 隐式相框照片上传 */}
      <input
        ref={adaptiveFileInputRef}
        type="file"
        accept="image/*"
        className="hidden"
        onChange={async (e) => {
          const f = e.target.files?.[0] || null;
          e.currentTarget.value = "";
          if (!f) return;
          setImageUploadLoading(true);
          try {
            const url = await uploadLocalImage(f);
            await handlePreview("MY_ADAPTIVE", { photo_url: url });
          } catch (err) {
            const msg = err instanceof Error ? err.message : t(locale, "preview.modal.image.need_file", "Please choose a local image");
            showToast(msg, "error");
          } finally {
            setImageUploadLoading(false);
          }
        }}
      />

      {/* 顶部标题与介绍 */}
      <div className="mb-6 flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between border-b border-ink/10 pb-4">
        <div>
          <h1 className="font-serif text-3xl font-bold text-ink tracking-tight flex items-center gap-2.5">
            <span>{t(locale, "preview.title", "No-device Demo")}</span>
            <span className="text-xs px-2 py-0.5 rounded-full bg-ink text-white font-sans font-medium">
              E-Ink Engine
            </span>
          </h1>
          <p className="text-ink-light text-sm mt-1">
            {locale === "zh"
              ? "在左侧按【生活、效率、资讯】探索日益丰富的墨水屏组件，右侧窗口即点即显、实时渲染排版。"
              : "Explore lifestyle, productivity, and news components on the left; live e-ink render on the right."}
          </p>
        </div>

        {/* 快捷新建自定义模式按钮 */}
        <button
          onClick={() => {
            setShowCustomModeModal(true);
            setCustomDesc("");
            setCustomModeName("");
            setCustomJson("");
            setCustomGenerating(false);
          }}
          className="rounded-sm border border-dashed border-ink/30 bg-white px-3.5 py-2 text-xs font-medium flex items-center gap-2 text-ink hover:border-ink hover:bg-paper-dark transition-colors shrink-0 shadow-xs"
        >
          <Plus size={15} />
          <span>{locale === "zh" ? "新建自定义模式" : "Create Custom Mode"}</span>
        </button>
      </div>

      {/* 左右分栏现代响应式架构：左侧模式库，右侧横置固定预览窗口 */}
      <div className="grid grid-cols-1 lg:grid-cols-[1fr_460px] xl:grid-cols-[1fr_500px] 2xl:grid-cols-[1fr_540px] gap-6 xl:gap-8 items-start">
        
        {/* 左侧：分类导航、二级子目录与分页展示容器 */}
        <div className="space-y-6">
          {/* 一级分类导航栏 (生活、效率、资讯、全部) + 搜索 */}
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 bg-paper-dark/80 p-2 rounded-sm border border-ink/10">
            <div className="flex items-center gap-1.5 overflow-x-auto">
              {[
                { id: "all", label: locale === "zh" ? "全部模式" : "All Modes", icon: Layers },
                { id: "life", label: locale === "zh" ? "🌿 生活日常" : "🌿 Life", icon: Heart },
                { id: "productivity", label: locale === "zh" ? "⚡ 效率工作" : "⚡ Productivity", icon: Briefcase },
                { id: "news", label: locale === "zh" ? "📰 资讯热点" : "📰 News & Alerts", icon: Newspaper },
              ].map((tab) => {
                const isActive = primaryTab === tab.id;
                return (
                  <button
                    key={tab.id}
                    onClick={() => setPrimaryTab(tab.id as PrimaryCategory)}
                    className={`px-3 py-1.5 rounded-sm text-xs font-medium transition-all whitespace-nowrap flex items-center gap-1.5 ${
                      isActive
                        ? "bg-ink text-white shadow-xs font-semibold"
                        : "text-ink-light hover:text-ink hover:bg-white/60"
                    }`}
                  >
                    <span>{tab.label}</span>
                  </button>
                );
              })}
            </div>

            {/* 搜索框 */}
            <div className="relative w-full sm:w-48">
              <Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-ink-light" />
              <input
                type="text"
                value={searchKeyword}
                onChange={(e) => setSearchKeyword(e.target.value)}
                placeholder={locale === "zh" ? "搜索模式..." : "Filter modes..."}
                className="w-full pl-8 pr-3 py-1 text-xs rounded-sm border border-ink/20 bg-white focus:outline-hidden focus:border-ink transition-colors"
              />
            </div>
          </div>

          {modesError ? (
            <div className="p-3 rounded-sm border border-amber-200 bg-amber-50 text-amber-800 text-xs flex items-center gap-2">
              <AlertCircle size={16} />
              <span>{modesError}</span>
            </div>
          ) : null}

          {/* 二级子标题 1：核心推荐模式 */}
          <PaginatedModeSection
            title={locale === "zh" ? "核心模式" : "Core Modes"}
            subtitle={locale === "zh" ? "精选推荐组件" : "Featured"}
            icon={Sparkles}
            modes={coreModes}
            currentMode={previewMode}
            onPreview={handleModeCardClick}
            onConfigure={handleOpenConfigModal}
            customMeta={modeMeta}
            locale={locale}
            pageSize={8}
          />

          {/* 二级子标题 2：更多丰富模式（包含全网热点、自然灾害预警等） */}
          <PaginatedModeSection
            title={locale === "zh" ? "更多模式" : "More Modes"}
            subtitle={locale === "zh" ? "多元场景与深度资讯" : "Extended"}
            icon={Layers}
            modes={moreModes}
            currentMode={previewMode}
            onPreview={handleModeCardClick}
            onConfigure={handleOpenConfigModal}
            customMeta={modeMeta}
            locale={locale}
            pageSize={8}
          />

          {/* 二级子标题 3：自定义与扩展模式 */}
          <PaginatedModeSection
            title={locale === "zh" ? "自定义模式" : "Custom Modes"}
            subtitle={locale === "zh" ? "用户定制与开放集成" : "User & Open Integration"}
            icon={Sliders}
            modes={customModes}
            currentMode={previewMode}
            onPreview={handleModeCardClick}
            onConfigure={handleOpenConfigModal}
            customMeta={modeMeta}
            locale={locale}
            pageSize={8}
            tailItem={
              <button
                onClick={() => {
                  setShowCustomModeModal(true);
                  setCustomDesc("");
                  setCustomModeName("");
                  setCustomJson("");
                }}
                className="rounded-sm border border-dashed border-ink/25 bg-white p-3 text-left flex flex-col justify-center items-center gap-1.5 hover:border-ink hover:bg-paper-dark transition-colors min-h-[78px]"
              >
                <Plus size={18} className="text-ink-light" />
                <span className="text-xs font-semibold text-ink">
                  {locale === "zh" ? "新建模式" : "New Mode"}
                </span>
              </button>
            }
          />
        </div>

        {/* 右侧：横向固定墨水屏实时预览窗口 (Sticky) */}
        <div className="sticky top-6 z-20 space-y-4">
          <Card className="border-ink/20 shadow-md bg-white">
            <CardHeader className="pb-3 border-b border-ink/10">
              <div className="flex items-center justify-between gap-2 flex-wrap">
                <div>
                  <span className="text-sm font-bold text-ink flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
                    {locale === "zh" ? "墨水屏实时预览" : "E-Ink Live Preview"}
                  </span>
                </div>

                {/* 屏幕尺寸与颜色模式快速切换 */}
                <div className="flex items-center gap-2">
                  <ColorSelect
                    value={previewColors}
                    onChange={(c) => {
                      setPreviewColors(c);
                      handlePreview(previewMode);
                    }}
                    tr={(zh, en) => (locale === "zh" ? zh : en)}
                  />
                  <ScreenSizeSelect
                    width={previewWidth}
                    height={previewHeight}
                    onChange={(w, h) => {
                      setPreviewWidth(w);
                      setPreviewHeight(h);
                      handlePreview(previewMode);
                    }}
                    tr={(zh, en) => (locale === "zh" ? zh : en)}
                  />
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handlePreview(previewMode)}
                    disabled={previewLoading}
                    className="h-8 px-2 text-xs"
                    title={locale === "zh" ? "重新渲染刷新" : "Refresh"}
                  >
                    <RefreshCw size={13} className={previewLoading ? "animate-spin" : ""} />
                  </Button>
                </div>
              </div>

              {/* 当前激活模式信息横条 */}
              <div className="mt-2.5 flex items-center justify-between gap-2 pt-2 border-t border-ink/5">
                <div className="flex items-center gap-2 truncate">
                  <span className="text-xs font-bold text-ink truncate">
                    {previewModeName}
                  </span>
                  <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-ink/5 text-ink-light">
                    {previewMode}
                  </span>
                </div>

                {/* 若当前模式支持调节，提供常驻配置入口 */}
                {CONFIGURABLE_MODES[previewMode] ? (
                  <button
                    onClick={() => handleOpenConfigModal(previewMode)}
                    className="text-xs font-medium text-ink bg-paper-dark hover:bg-ink hover:text-white px-2.5 py-1 rounded-sm border border-ink/15 flex items-center gap-1 transition-colors shrink-0"
                  >
                    <Sliders size={12} />
                    <span>{locale === "zh" ? "参数调节" : "Settings"}</span>
                  </button>
                ) : null}
              </div>
            </CardHeader>

            <CardContent className="p-4 flex flex-col items-center">
              {/* 墨水屏设备仿真画框 (带边框与阴影) */}
              <div
                className="relative w-full rounded-sm border-2 border-ink/80 bg-paper-light p-2 shadow-inner flex flex-col items-center justify-center overflow-hidden"
                style={{ aspectRatio: `${previewWidth} / ${previewHeight}` }}
              >
                {previewLoading ? (
                  <div className="absolute inset-0 z-10 bg-white/80 backdrop-blur-2xs flex flex-col items-center justify-center">
                    <Loader2 size={32} className="animate-spin text-ink mb-2" />
                    <p className="text-xs font-medium text-ink">
                      {t(locale, "preview.state.generating", "Generating preview...")}
                    </p>
                  </div>
                ) : null}

                {previewImageUrl ? (
                  <div className="relative w-full h-full bg-white flex items-center justify-center overflow-hidden rounded-xs">
                    <Image
                      src={previewImageUrl}
                      alt={t(locale, "preview.display.alt", "InkSight preview")}
                      fill
                      className="object-contain"
                      unoptimized
                    />
                  </div>
                ) : (
                  <div className="text-center p-6">
                    <Eye size={36} className="mx-auto text-ink-light mb-2 opacity-50" />
                    <p className="text-xs text-ink-light">
                      {locale === "zh" ? "点击左侧模式卡片立即呈现预览" : "Click any mode on the left to render"}
                    </p>
                  </div>
                )}
              </div>

              {/* 底部状态指示条 */}
              <div className="w-full mt-3 flex items-center justify-between text-[11px] text-ink-light px-1">
                <div className="truncate">
                  {previewLlmStatus ? (
                    <span className="text-ink font-medium">● {previewLlmStatus}</span>
                  ) : (
                    <span>● {previewWidth}×{previewHeight} · {previewColors >= 3 ? "3-Color BWR" : "1-Bit BW"}</span>
                  )}
                </div>
                {previewImageUrl ? (
                  <a
                    href={previewImageUrl}
                    download={`inksight-${previewMode.toLowerCase()}-${previewWidth}x${previewHeight}.png`}
                    className="hover:text-ink flex items-center gap-1 transition-colors"
                  >
                    <Download size={12} />
                    <span>{locale === "zh" ? "保存图像" : "Export"}</span>
                  </a>
                ) : null}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* 消息 Toast */}
      {toast ? (
        <div
          className={`fixed bottom-6 right-6 z-50 px-4 py-2.5 rounded-sm text-xs font-medium shadow-xl animate-fade-in flex items-center gap-2 ${
            toast.type === "success"
              ? "bg-green-600 text-white"
              : toast.type === "error"
              ? "bg-red-600 text-white"
              : "bg-ink text-white"
          }`}
        >
          {toast.type === "success" ? <Check size={14} /> : <AlertCircle size={14} />}
          <span>{toast.msg}</span>
        </div>
      ) : null}

      {/* 参数调整 Modal 弹窗 */}
      {modal ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/45 backdrop-blur-2xs" onClick={() => setModal(null)} />
          <div className="relative w-full max-w-lg rounded-sm border border-ink/20 bg-white shadow-2xl overflow-hidden">
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
                    ? (locale === "zh" ? "习惯打卡打卡项" : "Habit Tracker")
                    : modal.type === "calendar"
                    ? (locale === "zh" ? "日历提醒设置" : "Calendar Reminders")
                    : modal.type === "timetable"
                    ? (locale === "zh" ? "课程表设置" : "Timetable Settings")
                    : modal.type === "rss"
                    ? (locale === "zh" ? "RSS 订阅设置" : "RSS Settings")
                    : modal.type === "crypto"
                    ? (locale === "zh" ? "资产行情设置" : "Crypto Ticker Settings")
                    : modal.type === "webhook"
                    ? (locale === "zh" ? "开放数据卡片模拟" : "Webhook Card Simulator")
                    : (locale === "zh" ? "人生进度条设置" : "Life Progress Settings")}
                </span>
              </div>
              <button
                className="text-ink-light hover:text-ink text-sm p-1"
                onClick={() => setModal(null)}
              >
                ✕
              </button>
            </div>

            <div className="p-5 space-y-4 max-h-[75vh] overflow-y-auto">
              {/* 1. HOTLIST 全网热点平台多选！ */}
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
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setModal(null)}
                      >
                        {locale === "zh" ? "取消" : "Cancel"}
                      </Button>
                      <Button
                        size="sm"
                        onClick={async () => {
                          setModal(null);
                          await handlePreview("HOTLIST", { platforms: hotlistPlatforms });
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

                  {/* 预警级别选择 */}
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

                  {/* 灾害类型选择 */}
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

                  {/* 自定义预警通告文本 */}
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
                    <Button variant="outline" size="sm" onClick={() => setModal(null)}>
                      {locale === "zh" ? "取消" : "Cancel"}
                    </Button>
                    <Button
                      size="sm"
                      onClick={async () => {
                        setModal(null);
                        await handlePreview("DISASTER_ALERT", {
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
                /* 3. WEATHER 天气设置 */
                <div className="space-y-3">
                  <div className="text-xs text-ink-light">
                    {locale === "zh" ? "搜索并选择具体城市或地区：" : "Search and choose a specific location:"}
                  </div>
                  <LocationPicker
                    value={weatherDraftLocation}
                    onChange={setWeatherDraftLocation}
                    locale={locale === "zh" ? "zh" : "en"}
                    placeholder={locale === "zh" ? "输入城市名称（如：杭州、北京、Tokyo）" : "Enter city name..."}
                    className="w-full rounded-sm border border-ink/20 px-3 py-2 text-sm bg-white"
                    autoFocus
                  />
                  <div className="pt-3 flex items-center justify-end gap-2 border-t border-ink/10">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        setWeatherDraftLocation({ city: "杭州" });
                      }}
                    >
                      {locale === "zh" ? "设为杭州" : "Reset"}
                    </Button>
                    <Button
                      size="sm"
                      onClick={async () => {
                        const loc = cleanLocationValue(weatherDraftLocation);
                        setModal(null);
                        await handlePreview("WEATHER", loc.city ? loc : {});
                      }}
                      disabled={previewLoading}
                    >
                      {locale === "zh" ? "应用并预览" : "Apply"}
                    </Button>
                  </div>
                </div>
              ) : modal.type === "memo" ? (
                /* 4. MEMO 便签设置 */
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
                    <Button variant="outline" size="sm" onClick={() => setModal(null)}>
                      {locale === "zh" ? "取消" : "Cancel"}
                    </Button>
                    <Button
                      size="sm"
                      onClick={async () => {
                        setModal(null);
                        await handlePreview("MEMO", {
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
                /* 5. RSS 设置 */
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
                    <Button variant="outline" size="sm" onClick={() => setModal(null)}>
                      取消
                    </Button>
                    <Button
                      size="sm"
                      onClick={async () => {
                        setModal(null);
                        await handlePreview("RSS", {
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
                /* 6. CRYPTO 资产行情设置 */
                <div className="space-y-3">
                  <label className="text-xs font-semibold text-ink block">资产代号 (Symbol)：</label>
                  <div className="flex flex-wrap gap-2">
                    {["BTC", "ETH", "SOL", "BNB", "DOGE"].map((sym) => (
                      <button
                        key={sym}
                        type="button"
                        onClick={() => setCryptoSymbol(sym)}
                        className={`px-3 py-1 rounded-sm border text-xs font-mono ${
                          cryptoSymbol === sym ? "bg-ink text-white border-ink" : "bg-white border-ink/20 text-ink"
                        }`}
                      >
                        {sym}
                      </button>
                    ))}
                  </div>
                  <input
                    value={cryptoSymbol}
                    onChange={(e) => setCryptoSymbol(e.target.value.toUpperCase())}
                    className="w-full rounded-sm border border-ink/20 px-3 py-1.5 text-xs bg-white font-mono uppercase"
                    placeholder="输入其他代号..."
                  />
                  <div className="pt-3 flex items-center justify-end gap-2 border-t border-ink/10">
                    <Button variant="outline" size="sm" onClick={() => setModal(null)}>
                      取消
                    </Button>
                    <Button
                      size="sm"
                      onClick={async () => {
                        setModal(null);
                        await handlePreview("CRYPTO", { symbol: cryptoSymbol });
                      }}
                    >
                      应用并预览
                    </Button>
                  </div>
                </div>
              ) : (
                /* 其他通用模式弹窗 */
                <div className="space-y-3">
                  <p className="text-xs text-ink-light">已加载该模式快捷配置参数。</p>
                  <div className="pt-3 flex items-center justify-end gap-2 border-t border-ink/10">
                    <Button variant="outline" size="sm" onClick={() => setModal(null)}>
                      关闭
                    </Button>
                    <Button
                      size="sm"
                      onClick={async () => {
                        setModal(null);
                        await handlePreview(modal.modeId);
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
      ) : null}

      {/* 自定义模式生成弹窗 */}
      {showCustomModeModal ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/45 backdrop-blur-2xs" onClick={() => setShowCustomModeModal(false)} />
          <div className="relative w-full max-w-lg rounded-sm border border-ink/20 bg-white p-5 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-ink/10 pb-3">
              <h3 className="text-sm font-bold text-ink">
                {locale === "zh" ? "AI 智能生成自定义墨水屏模式" : "Generate Custom Mode"}
              </h3>
              <button className="text-ink-light hover:text-ink text-sm" onClick={() => setShowCustomModeModal(false)}>
                ✕
              </button>
            </div>
            <div className="space-y-2">
              <label className="text-xs font-semibold text-ink block">
                {locale === "zh" ? "描述你想要的墨水屏排版与功能：" : "Describe desired mode layout:"}
              </label>
              <textarea
                value={customDesc}
                onChange={(e) => setCustomDesc(e.target.value)}
                placeholder={locale === "zh" ? "例如：一个展示三行每日复盘清单、一个大号完成度进度条，带古典双线边框的极简卡片..." : "Describe the layout..."}
                rows={4}
                className="w-full rounded-sm border border-ink/20 p-2.5 text-xs bg-white"
              />
            </div>
            <div className="flex items-center justify-end gap-2 pt-2">
              <Button variant="outline" size="sm" onClick={() => setShowCustomModeModal(false)}>
                {locale === "zh" ? "取消" : "Cancel"}
              </Button>
              <Button
                size="sm"
                onClick={handleGenerateCustomModeAndPreview}
                disabled={customGenerating || !customDesc.trim()}
                className="bg-ink text-white"
              >
                {customGenerating ? (
                  <>
                    <Loader2 size={13} className="animate-spin mr-1.5" />
                    <span>{locale === "zh" ? "生成中..." : "Generating..."}</span>
                  </>
                ) : (
                  <span>{locale === "zh" ? "开始生成并预览" : "Generate & Preview"}</span>
                )}
              </Button>
            </div>
          </div>
        </div>
      ) : null}

      {/* 邀请码弹窗 */}
      {showInviteModal ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/45 backdrop-blur-2xs" onClick={() => setShowInviteModal(false)} />
          <div className="relative w-full max-w-md rounded-sm border border-ink/20 bg-white p-5 shadow-2xl space-y-4">
            <h3 className="text-sm font-bold text-ink">
              {locale === "zh" ? "输入邀请码解锁额度" : "Enter Invitation Code"}
            </h3>
            <p className="text-xs text-ink-light">
              {locale === "zh" ? "体验免费额度已达上限，请输入专属邀请码兑换更多预览点数。" : "Free quota exhausted, please enter invite code."}
            </p>
            <input
              value={inviteCode}
              onChange={(e) => setInviteCode(e.target.value)}
              placeholder={locale === "zh" ? "输入邀请码" : "Invitation Code"}
              className="w-full rounded-sm border border-ink/20 px-3 py-2 text-xs bg-white font-mono"
            />
            <div className="flex items-center justify-end gap-2">
              <Button variant="outline" size="sm" onClick={() => setShowInviteModal(false)}>
                {locale === "zh" ? "关闭" : "Close"}
              </Button>
              <Button
                size="sm"
                onClick={async () => {
                  if (!inviteCode.trim()) return;
                  setRedeemingInvite(true);
                  try {
                    const res = await fetch("/api/auth/redeem-invite-code", {
                      method: "POST",
                      headers: { "Content-Type": "application/json" },
                      body: JSON.stringify({ invite_code: inviteCode.trim() }),
                    });
                    const d = await res.json();
                    if (!res.ok) throw new Error(d.error || "兑换失败");
                    showToast(locale === "zh" ? "兑换成功！" : "Redeemed successfully!", "success");
                    setShowInviteModal(false);
                    if (pendingPreviewMode) {
                      await handlePreview(pendingPreviewMode);
                    }
                  } catch (err) {
                    showToast(err instanceof Error ? err.message : "兑换失败", "error");
                  } finally {
                    setRedeemingInvite(false);
                  }
                }}
                disabled={redeemingInvite || !inviteCode.trim()}
              >
                {locale === "zh" ? "立即兑换" : "Redeem"}
              </Button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
