"use client";

import { useEffect, useState } from "react";
import { Terminal, ChevronDown, ChevronUp, AlertCircle, CheckCircle2 } from "lucide-react";

interface LayoutInspectorPanelProps {
  modeId: string;
  width: number;
  height: number;
  locale: string;
}

interface LayoutSessionData {
  mode_id: string;
  screen: string;
  fill_ratio_percent: number;
  remaining_height_px: number;
  density_assessment: "sparse" | "balanced" | "crowded";
  has_truncation: boolean;
  warnings: string[];
}

export function LayoutInspectorPanel({
  modeId,
  width,
  height,
  locale,
}: LayoutInspectorPanelProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [session, setSession] = useState<LayoutSessionData | null>(null);
  const [asciiPreview, setAsciiPreview] = useState<string>("");

  useEffect(() => {
    if (!isOpen || !modeId) return;

    let mounted = true;
    setLoading(true);

    fetch(`/api/modes/${encodeURIComponent(modeId)}/layout-session?w=${width}&h=${height}&format=json`)
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (!mounted || !data || !data.ok) return;
        setSession(data.session);
        // 提取 ASCII 拓扑
        const rawDialogue = String(data.ai_dialogue || "");
        const match = rawDialogue.match(/```text\n([\s\S]*?)\n```/);
        if (match && match[1]) {
          setAsciiPreview(match[1]);
        } else {
          setAsciiPreview("");
        }
      })
      .catch(() => {})
      .finally(() => {
        if (mounted) setLoading(false);
      });

    return () => {
      mounted = false;
    };
  }, [isOpen, modeId, width, height]);

  return (
    <div className="w-full mt-3 border border-ink/10 rounded-sm bg-paper-light/50 dark:bg-zinc-900/50 text-xs">
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="w-full px-3 py-2 flex items-center justify-between font-medium text-ink hover:bg-ink/5 transition-colors cursor-pointer"
      >
        <div className="flex items-center gap-1.5">
          <Terminal size={13} className="text-ink-light" />
          <span>{locale === "zh" ? "AI 空间排版与版面拓扑诊断" : "AI Layout & Spatial Inspector"}</span>
          {session ? (
            <span
              className={`ml-2 text-[10px] px-1.5 py-0.2 rounded font-mono ${
                session.has_truncation
                  ? "bg-red-100 text-red-700"
                  : session.density_assessment === "balanced"
                  ? "bg-green-100 text-green-700"
                  : "bg-amber-100 text-amber-700"
              }`}
            >
              {session.has_truncation ? "截断警告" : `${session.fill_ratio_percent}% 占用`}
            </span>
          ) : null}
        </div>
        {isOpen ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
      </button>

      {isOpen ? (
        <div className="p-3 border-t border-ink/10 flex flex-col gap-2.5">
          {loading ? (
            <div className="text-center py-3 text-ink-light font-mono">
              {locale === "zh" ? "排版探针测算中..." : "Analyzing spatial layout..."}
            </div>
          ) : session ? (
            <>
              {/* 指标看板 */}
              <div className="grid grid-cols-3 gap-2 text-[11px]">
                <div className="p-2 rounded bg-white dark:bg-zinc-950 border border-ink/5 flex flex-col">
                  <span className="text-ink-light text-[10px]">{locale === "zh" ? "空间利用率" : "Fill Ratio"}</span>
                  <span className="font-bold text-ink font-mono">{session.fill_ratio_percent}%</span>
                </div>
                <div className="p-2 rounded bg-white dark:bg-zinc-950 border border-ink/5 flex flex-col">
                  <span className="text-ink-light text-[10px]">{locale === "zh" ? "安全余量" : "Safe Margin"}</span>
                  <span className="font-bold text-ink font-mono">{session.remaining_height_px} px</span>
                </div>
                <div className="p-2 rounded bg-white dark:bg-zinc-950 border border-ink/5 flex flex-col">
                  <span className="text-ink-light text-[10px]">{locale === "zh" ? "排版状态" : "Status"}</span>
                  <span className="font-bold flex items-center gap-1">
                    {session.has_truncation ? (
                      <span className="text-red-600 flex items-center gap-0.5">
                        <AlertCircle size={11} />
                        {locale === "zh" ? "截断" : "Truncated"}
                      </span>
                    ) : (
                      <span className="text-green-600 flex items-center gap-0.5">
                        <CheckCircle2 size={11} />
                        {locale === "zh" ? "完整" : "Optimal"}
                      </span>
                    )}
                  </span>
                </div>
              </div>

              {/* ASCII 拓扑 */}
              {asciiPreview ? (
                <div className="flex flex-col gap-1">
                  <span className="text-[10px] font-bold text-ink-light">
                    {locale === "zh" ? "点阵拓扑投影 (ASCII Projection):" : "Spatial Topology:"}
                  </span>
                  <pre className="p-2 rounded bg-zinc-950 text-zinc-100 font-mono text-[9px] leading-tight overflow-x-auto select-all">
                    {asciiPreview}
                  </pre>
                </div>
              ) : null}

              {/* 告警建议 */}
              {session.warnings && session.warnings.length > 0 ? (
                <div className="text-[10px] text-amber-700 bg-amber-50 dark:bg-amber-950/30 p-2 rounded border border-amber-200 dark:border-amber-900/50">
                  <p className="font-bold mb-1">{locale === "zh" ? "排版调优提示:" : "Inspection Notes:"}</p>
                  <ul className="list-disc pl-3.5 space-y-0.5">
                    {session.warnings.map((w, idx) => (
                      <li key={idx}>{w}</li>
                    ))}
                  </ul>
                </div>
              ) : null}
            </>
          ) : (
            <div className="text-ink-light text-center py-2">
              {locale === "zh" ? "未能获取该模式的排版数据" : "No layout data available"}
            </div>
          )}
        </div>
      ) : null}
    </div>
  );
}
