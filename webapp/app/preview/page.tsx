"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import {
  AlertCircle,
  Plus,
  Sparkles,
  Layers,
  Heart,
  Briefcase,
  Newspaper,
  Sliders,
  Check,
  Search,
} from "lucide-react";
import { localeFromPathname, t, withLocalePath } from "@/lib/i18n";
import { authHeaders, fetchCurrentUser } from "@/lib/auth";

import {
  type ModeCatalogItem,
  type PrimaryCategory,
  MODE_PRIMARY_CATEGORY,
  CONFIGURABLE_MODES,
  STORAGE_KEY_DEFAULT_TICKER,
} from "@/components/preview/types";
import { PaginatedModeSection } from "@/components/preview/mode-section";
import { PreviewCanvas } from "@/components/preview/preview-canvas";
import { ModeConfigModal } from "@/components/preview/mode-config-modal";
import { CustomModeDialog } from "@/components/preview/custom-mode-dialog";
import { InviteDialog } from "@/components/preview/invite-dialog";

export default function ExperiencePage() {
  const router = useRouter();
  const pathname = usePathname();
  const locale = localeFromPathname(pathname || "/");

  const [authChecked, setAuthChecked] = useState(false);
  const [userLlmApiKey, setUserLlmApiKey] = useState<string>("");

  const [catalogItems, setCatalogItems] = useState<ModeCatalogItem[]>([]);
  const [modesError, setModesError] = useState<string | null>(null);

  // 默认启动模式与显示参数
  const [previewMode, setPreviewMode] = useState("HOTLIST");
  const [previewColors, setPreviewColors] = useState(3);
  const [previewWidth, setPreviewWidth] = useState(400);
  const [previewHeight, setPreviewHeight] = useState(300);
  const [previewModeNameOverride, setPreviewModeNameOverride] = useState<string | null>(null);

  // 一级分类标签与搜索
  const [primaryTab, setPrimaryTab] = useState<PrimaryCategory>("all");
  const [searchKeyword, setSearchKeyword] = useState<string>("");

  // 状态反馈
  const [previewLoading, setPreviewLoading] = useState(false);
  const [_previewError, setPreviewError] = useState<string | null>(null);
  const [toast, setToast] = useState<{ msg: string; type: "success" | "error" | "info" } | null>(null);
  const [previewLlmStatus, setPreviewLlmStatus] = useState<string | null>(null);
  const [previewImageUrl, setPreviewImageUrl] = useState<string | null>(null);
  const lastObjectUrlRef = useRef<string | null>(null);
  const toastTimerRef = useRef<number | null>(null);

  // 参数配置模态窗状态
  const [modal, setModal] = useState<null | {
    type: "quote" | "weather" | "memo" | "countdown" | "habit" | "lifebar" | "calendar" | "timetable" | "rss" | "crypto" | "hotlist" | "disaster" | "webhook";
    modeId: string;
  }>(null);

  // 默认持久状态
  const [hotlistPlatforms, setHotlistPlatforms] = useState<string[]>(["zhihu", "weibo"]);
  const [disasterLevel, setDisasterLevel] = useState<string>("红色");
  const [disasterHazard, setDisasterHazard] = useState<string>("暴雨");
  const [rssFeedUrl, _setRssFeedUrl] = useState("https://kellson.dpdns.org:81/playno1/av");
  const [cryptoSymbol, setCryptoSymbol] = useState("BTC");

  // 自定义模式与邀请码弹窗状态
  const [showCustomModeModal, setShowCustomModeModal] = useState(false);
  const [showInviteModal, setShowInviteModal] = useState(false);
  const [pendingPreviewMode, setPendingPreviewMode] = useState<string | null>(null);

  const adaptiveFileInputRef = useRef<HTMLInputElement | null>(null);

  const showToast = (msg: string, type: "success" | "error" | "info" = "info") => {
    setToast({ msg, type });
    if (toastTimerRef.current) window.clearTimeout(toastTimerRef.current);
    toastTimerRef.current = window.setTimeout(() => setToast(null), 2500);
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

    try {
      const savedTicker = localStorage.getItem(STORAGE_KEY_DEFAULT_TICKER);
      if (savedTicker && savedTicker.trim()) {
        setCryptoSymbol(savedTicker.trim().toUpperCase());
      }
    } catch {}
  }, []);

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
      if (primaryTab !== "all") {
        const prim = MODE_PRIMARY_CATEGORY[mid] || (item.category === "custom" ? "productivity" : "life");
        if (prim !== primaryTab) return false;
      }
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
   * 核心预览请求处理器
   */
  const handlePreview = async (
    modeId?: string,
    override?: Record<string, unknown>,
    colorOverride?: number,
    sizeOverride?: { w: number; h: number },
  ) => {
    const targetMode = modeId || previewMode;
    if (!targetMode || !authChecked) return;

    const effColors = colorOverride !== undefined ? colorOverride : previewColors;
    const effWidth = sizeOverride ? sizeOverride.w : previewWidth;
    const effHeight = sizeOverride ? sizeOverride.h : previewHeight;

    setPreviewLlmStatus(null);
    setPreviewLoading(true);
    setPreviewError(null);

    try {
      const params = new URLSearchParams();
      params.set("persona", targetMode);
      params.set("ui_language", locale === "en" ? "en" : "zh");
      params.set("colors", String(effColors));
      params.set("w", String(effWidth));
      params.set("h", String(effHeight));

      const mergedOverride: Record<string, unknown> = { ...(override || {}) };

      if (targetMode === "HOTLIST" && !mergedOverride.platforms && !mergedOverride.platform) {
        mergedOverride.platforms = hotlistPlatforms;
      }
      if (targetMode === "DISASTER_ALERT") {
        if (!mergedOverride.level) mergedOverride.level = disasterLevel;
        if (!mergedOverride.hazard) mergedOverride.hazard = disasterHazard;
      }
      if ((targetMode === "CRYPTO" || targetMode === "MARKET") && !mergedOverride.symbol) {
        mergedOverride.symbol = cryptoSymbol;
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
        const ct = res.headers.get("content-type") || "";
        if (ct.includes("image/")) {
          const blob = await res.blob();
          const objectUrl = URL.createObjectURL(blob);
          if (lastObjectUrlRef.current) URL.revokeObjectURL(lastObjectUrlRef.current);
          lastObjectUrlRef.current = objectUrl;
          setPreviewImageUrl(objectUrl);
          throw new Error(locale === "zh" ? `后端渲染异常 (HTTP ${res.status})` : `Render error (HTTP ${res.status})`);
        }
        let errText = "";
        try {
          const data = await res.json();
          errText = data.message || data.error || JSON.stringify(data);
        } catch {
          errText = await res.text().catch(() => "Unknown error");
        }
        if (errText.includes("PNG") || errText.includes("IHDR")) {
          errText = locale === "zh" ? "后端渲染图像异常" : "Backend image render error";
        }
        throw new Error(`HTTP ${res.status}: ${errText.substring(0, 100)}`);
      }

      const statusHeader = res.headers.get("x-preview-status");
      const llmRequired = res.headers.get("x-llm-required");
      if (statusHeader === "no_llm_required" || llmRequired === "0") {
        setPreviewLlmStatus(null);
      } else if (statusHeader === "static_served") {
        setPreviewLlmStatus(locale === "zh" ? "静态内容已加载" : "Static content served");
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
      const msg = err instanceof Error ? err.message : "Preview failed";
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
   * 打开配置弹窗
   */
  const handleOpenConfigModal = (modeId: string) => {
    setPreviewMode(modeId);
    const cfgType = CONFIGURABLE_MODES[modeId];
    if (cfgType) {
      setModal({ type: cfgType as never, modeId });
    }
  };

  // 接收配置表单提交
  const handleModalSubmit = async (modeId: string, override: Record<string, unknown>) => {
    if (modeId === "HOTLIST" && Array.isArray(override.platforms)) {
      setHotlistPlatforms(override.platforms as string[]);
    }
    if (modeId === "DISASTER_ALERT") {
      if (override.level) setDisasterLevel(String(override.level));
      if (override.hazard) setDisasterHazard(String(override.hazard));
    }
    if ((modeId === "CRYPTO" || modeId === "MARKET") && override.symbol) {
      const sym = String(override.symbol).toUpperCase();
      setCryptoSymbol(sym);
      try {
        localStorage.setItem(STORAGE_KEY_DEFAULT_TICKER, sym);
      } catch {}
      showToast(
        locale === "zh" ? `已保存并切换行情标的: ${sym}` : `Saved & switched ticker: ${sym}`,
        "success"
      );
    }
    await handlePreview(modeId, override);
  };

  // 加载目录
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

  // 初始自动生成
  useEffect(() => {
    if (authChecked && catalogItems.length > 0 && !previewImageUrl && !previewLoading) {
      handlePreview("HOTLIST", { platforms: hotlistPlatforms });
    }
  }, [authChecked, catalogItems.length]);

  return (
    <div className="mx-auto max-w-7xl px-4 sm:px-6 py-6 sm:py-10">
      {/* 顶部标题栏 */}
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

        <button
          onClick={() => setShowCustomModeModal(true)}
          className="rounded-sm border border-dashed border-ink/30 bg-white px-3.5 py-2 text-xs font-medium flex items-center gap-2 text-ink hover:border-ink hover:bg-paper-dark transition-colors shrink-0 shadow-xs"
        >
          <Plus size={15} />
          <span>{locale === "zh" ? "新建自定义模式" : "Create Custom Mode"}</span>
        </button>
      </div>

      {/* 左右分栏现代响应式架构 */}
      <div className="grid grid-cols-1 lg:grid-cols-[1fr_460px] xl:grid-cols-[1fr_500px] 2xl:grid-cols-[1fr_540px] gap-6 xl:gap-8 items-start">
        
        {/* 左侧：分类导航、二级子目录与分页展示容器 */}
        <div className="space-y-6">
          {/* 一级分类导航栏 (生活、效率、资讯、全部) + 搜索 */}
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 bg-paper-dark/80 p-2 rounded-sm border border-ink/10">
            <div className="flex items-center gap-1.5 overflow-x-auto">
              {[
                { id: "all", label: locale === "zh" ? "全部模式" : "All Modes", icon: Layers },
                { id: "life", label: locale === "zh" ? "生活日常" : "Life", icon: Heart },
                { id: "productivity", label: locale === "zh" ? "效率工作" : "Productivity", icon: Briefcase },
                { id: "news", label: locale === "zh" ? "资讯热点" : "News & Alerts", icon: Newspaper },
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

          {/* 二级子标题 2：更多丰富模式 */}
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
                onClick={() => setShowCustomModeModal(true)}
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
          <PreviewCanvas
            previewMode={previewMode}
            previewModeName={previewModeName}
            previewWidth={previewWidth}
            previewHeight={previewHeight}
            previewColors={previewColors}
            previewImageUrl={previewImageUrl}
            previewLoading={previewLoading}
            previewLlmStatus={previewLlmStatus}
            locale={locale}
            onColorChange={(c) => {
              setPreviewColors(c);
              handlePreview(previewMode, undefined, c);
            }}
            onSizeChange={(w, h) => {
              setPreviewWidth(w);
              setPreviewHeight(h);
              handlePreview(previewMode, undefined, undefined, { w, h });
            }}
            onRefresh={() => handlePreview(previewMode)}
            onOpenConfig={handleOpenConfigModal}
          />
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

      {/* 模式参数调节 Modal */}
      {modal ? (
        <ModeConfigModal
          modal={modal}
          locale={locale}
          previewLoading={previewLoading}
          onClose={() => setModal(null)}
          onSubmit={handleModalSubmit}
          initialHotlistPlatforms={hotlistPlatforms}
          initialDisasterLevel={disasterLevel}
          initialDisasterHazard={disasterHazard}
          initialRssFeedUrl={rssFeedUrl}
          initialCryptoSymbol={cryptoSymbol}
        />
      ) : null}

      {/* AI 自定义模式生成弹窗 */}
      <CustomModeDialog
        isOpen={showCustomModeModal}
        locale={locale}
        onClose={() => setShowCustomModeModal(false)}
        onGenerated={async (modeDef) => {
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
          if (!res.ok) throw new Error(`HTTP ${res.status}`);
          const blob = await res.blob();
          const url = URL.createObjectURL(blob);
          if (lastObjectUrlRef.current) URL.revokeObjectURL(lastObjectUrlRef.current);
          lastObjectUrlRef.current = url;
          setPreviewImageUrl(url);
          setPreviewMode((modeDef as { mode_id?: string })?.mode_id?.toUpperCase() || "CUSTOM");
          setPreviewModeNameOverride((modeDef as { display_name?: string })?.display_name || "自定义模式");
          showToast(t(locale, "preview.toast.updated", "Preview updated"), "success");
        }}
        showToast={showToast}
      />

      {/* 邀请码弹窗 */}
      <InviteDialog
        isOpen={showInviteModal}
        locale={locale}
        onClose={() => setShowInviteModal(false)}
        onRedeemed={async () => {
          if (pendingPreviewMode) await handlePreview(pendingPreviewMode);
        }}
        showToast={showToast}
      />
    </div>
  );
}
