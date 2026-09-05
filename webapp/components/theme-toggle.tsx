"use client";

import { useEffect, useState } from "react";
import { Sun, Moon, Laptop } from "lucide-react";
import { useTheme } from "./theme-provider";

export function ThemeToggle() {
  const { theme, setTheme, resolvedTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) {
    return (
      <div className="w-8 h-8 rounded-md flex items-center justify-center text-ink-light opacity-50">
        <Sun size={18} />
      </div>
    );
  }

  const cycleTheme = () => {
    if (theme === "light") setTheme("dark");
    else if (theme === "dark") setTheme("system");
    else setTheme("light");
  };

  const getLabel = () => {
    if (theme === "system") return "跟随系统";
    if (theme === "dark") return "暗黑模式";
    return "日间模式";
  };

  return (
    <button
      onClick={cycleTheme}
      className="p-1.5 rounded-md text-ink-light hover:text-ink hover:bg-ink/[0.05] dark:text-zinc-400 dark:hover:text-zinc-100 dark:hover:bg-zinc-800 transition-colors flex items-center gap-1.5 text-xs"
      title={`当前主题: ${getLabel()} (点击切换)`}
      aria-label="切换网站主题"
    >
      {theme === "system" ? (
        <Laptop size={18} />
      ) : resolvedTheme === "dark" ? (
        <Moon size={18} />
      ) : (
        <Sun size={18} />
      )}
    </button>
  );
}
