"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Star, BookmarkPlus, Check, Plus } from "lucide-react";
import {
  POPULAR_STOCKS,
  POPULAR_CRYPTOS,
  SavedTickerItem,
  STORAGE_KEY_SAVED_TICKERS,
  STORAGE_KEY_DEFAULT_TICKER,
  DEFAULT_USER_SAVED_TICKERS,
} from "../types";

interface CryptoStockConfigProps {
  initialSymbol: string;
  locale: string;
  previewLoading: boolean;
  onClose: () => void;
  onSubmit: (symbol: string) => Promise<void>;
}

export function CryptoStockConfig({
  initialSymbol,
  locale,
  previewLoading,
  onClose,
  onSubmit,
}: CryptoStockConfigProps) {
  const [cryptoSymbol, setCryptoSymbol] = useState(initialSymbol || "BTC");
  const [savedTickers, setSavedTickers] = useState<SavedTickerItem[]>([]);
  const [defaultTicker, setDefaultTicker] = useState<string>("BTC");
  const [serverStocks, setServerStocks] = useState<{ symbol: string; name: string; is_custom?: boolean }[]>([]);
  const [isPersistingStock, setIsPersistingStock] = useState(false);
  const [persistSuccessMsg, setPersistSuccessMsg] = useState<string | null>(null);

  const refreshServerStocks = async () => {
    try {
      const res = await fetch("/api/market/stocks");
      if (res.ok) {
        const d = await res.json();
        if (d.success && Array.isArray(d.stocks)) {
          setServerStocks(d.stocks);
        }
      }
    } catch {}
  };

  useEffect(() => {
    refreshServerStocks();
  }, []);

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

  const handlePersistNewStock = async (sym: string, customName?: string) => {
    const clean = sym.trim().toUpperCase();
    if (!clean) return;
    setIsPersistingStock(true);
    setPersistSuccessMsg(null);
    try {
      const res = await fetch("/api/market/stocks", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ symbol: clean, name: customName || "" }),
      });
      if (res.ok) {
        const data = await res.json();
        if (data.success && data.stock) {
          const st = data.stock;
          setPersistSuccessMsg(locale === "zh" ? `已永久保存股票: ${st.symbol} (${st.name})` : `Saved stock: ${st.symbol}`);
          await refreshServerStocks();
          handleAddSavedTicker(clean, st.name);
          setCryptoSymbol(clean);
          setTimeout(() => setPersistSuccessMsg(null), 3500);
        }
      }
    } catch {} finally {
      setIsPersistingStock(false);
    }
  };

  const handleDeleteServerStock = async (sym: string, e?: React.MouseEvent) => {
    if (e) e.stopPropagation();
    try {
      const res = await fetch(`/api/market/stocks/${encodeURIComponent(sym)}`, {
        method: "DELETE",
      });
      if (res.ok) {
        await refreshServerStocks();
        handleRemoveSavedTicker(sym);
      }
    } catch {}
  };

  const handleAddSavedTicker = (sym: string, customName?: string) => {
    const clean = sym.trim().toUpperCase();
    if (!clean) return;
    setSavedTickers((prev) => {
      if (prev.some((item) => item.sym === clean)) return prev;
      const foundServer = serverStocks.find((s) => s.symbol === clean);
      const foundStock = POPULAR_STOCKS.find((s) => s.sym === clean);
      const foundCrypto = POPULAR_CRYPTOS.find((c) => c.sym === clean);
      const name = customName || (foundServer ? foundServer.name : foundStock ? foundStock.name : foundCrypto ? foundCrypto.name : undefined);
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

  return (
    <div className="space-y-4">
      <div className="text-xs text-ink-light leading-relaxed">
        {locale === "zh"
          ? "支持查阅与监控全球知名股票（美股/港股）与主流加密资产！支持将常用标的保存到自选列表或设为默认，方便下次一键调用。"
          : "Track global stocks (Apple, Tesla, NVIDIA...) and major crypto assets. Save favorite tickers or set default for quick access next time."}
      </div>

      {/* 输入框与快捷添加持久化股票 */}
      <div>
        <div className="flex items-center justify-between mb-1.5">
          <label className="text-xs font-semibold text-ink block">
            {locale === "zh" ? "输入股票代码或加密代号" : "Enter Stock / Crypto Symbol"}
          </label>
          {persistSuccessMsg ? (
            <span className="text-[11px] text-green-700 font-medium animate-fade-in flex items-center gap-1">
              <Check size={12} />
              {persistSuccessMsg}
            </span>
          ) : null}
        </div>
        <div className="flex gap-2">
          <input
            value={cryptoSymbol}
            onChange={(e) => setCryptoSymbol(e.target.value.toUpperCase())}
            className="flex-1 rounded-sm border border-ink/20 px-3 py-1.5 text-xs bg-white font-mono uppercase font-semibold"
            placeholder={locale === "zh" ? "输入任何股票或加密代码，如 AMD, NVDA, BTC..." : "e.g. AMD, NVDA, BTC, ETH..."}
          />
          {cryptoSymbol.trim() ? (
            <>
              <Button
                variant="outline"
                size="sm"
                disabled={isPersistingStock}
                onClick={() => handlePersistNewStock(cryptoSymbol)}
                className="text-xs px-2.5 flex items-center gap-1 bg-amber-50/50 border-amber-300 text-ink hover:bg-amber-100"
                title={locale === "zh" ? "将此股票代码持久化保存到系统与所有设备库中" : "Persist this stock symbol to system storage"}
              >
                <Plus size={13} className="text-amber-600" />
                <span>{isPersistingStock ? (locale === "zh" ? "保存中..." : "Saving...") : (locale === "zh" ? "持久化保存股票" : "Persist Stock")}</span>
              </Button>

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
                  className="text-xs px-2.5 flex items-center gap-1"
                  title={locale === "zh" ? "添加到本地常用自选标的" : "Add to favorites"}
                >
                  <BookmarkPlus size={13} className="text-ink-light" />
                  <span>{locale === "zh" ? "收进自选" : "Favorite"}</span>
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
            {locale === "zh" ? "暂无自选标的，输入代码后点击【持久化保存股票】或【收进自选】即可快速收纳。" : "No saved tickers yet. Enter a symbol and click 'Persist Stock' or 'Favorite'."}
          </div>
        )}
      </div>

      {/* 2. 持久化股票标的池 */}
      <div>
        <div className="text-xs font-semibold text-ink mb-1.5 flex items-center justify-between">
          <span>{locale === "zh" ? "持久化股票标的 (美股/港股，支持添加)" : "Persisted Global Stocks"}</span>
          <span className="text-[11px] font-normal text-ink-light">
            {locale === "zh" ? "点击一键选择" : "Click to select"}
          </span>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-1.5">
          {(serverStocks.length > 0 ? serverStocks : POPULAR_STOCKS.map((s) => ({ symbol: s.sym, name: s.name, is_custom: false }))).map((stk) => {
            const sym = stk.symbol;
            const isSelected = cryptoSymbol === sym;
            const isCustom = stk.is_custom;
            return (
              <div
                key={sym}
                onClick={() => setCryptoSymbol(sym)}
                className={`relative px-2.5 py-1.5 rounded-sm border text-left transition-all cursor-pointer ${
                  isSelected
                    ? "bg-ink text-white border-ink shadow-xs"
                    : "bg-paper-light border-ink/15 text-ink hover:border-ink/50 hover:bg-white"
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold font-mono leading-tight">{sym}</span>
                  {isCustom ? (
                    <button
                      type="button"
                      onClick={(e) => handleDeleteServerStock(sym, e)}
                      className={`text-[10px] p-0.5 rounded-xs transition-colors ${
                        isSelected ? "text-white/60 hover:text-white" : "text-ink-light hover:text-red-600"
                      }`}
                      title={locale === "zh" ? "从持久化股票库删除" : "Delete persisted stock"}
                    >
                      ✕
                    </button>
                  ) : null}
                </div>
                <div className={`text-[10px] truncate ${isSelected ? "text-white/80" : "text-ink-light"}`}>
                  {stk.name || sym}
                </div>
              </div>
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
              if (!POPULAR_CRYPTOS.some((c) => c.sym === targetSym)) {
                handlePersistNewStock(targetSym);
              }
              try {
                localStorage.setItem(STORAGE_KEY_DEFAULT_TICKER, targetSym);
              } catch {}
              await onSubmit(targetSym);
            }}
          >
            {locale === "zh" ? "保存并预览" : "Save & Preview"}
          </Button>
        </div>
      </div>
    </div>
  );
}
