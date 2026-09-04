"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";

// 1. MEMO
export function MemoConfig({
  locale,
  previewLoading,
  onClose,
  onSubmit,
}: {
  locale: string;
  previewLoading: boolean;
  onClose: () => void;
  onSubmit: (override: Record<string, unknown>) => Promise<void>;
}) {
  const [memoDraft, setMemoDraft] = useState({
    title1: "今日专注",
    text1: "重构与模块化解耦前端及后端服务",
    title2: "待办事项",
    text2: "1. 灾害模式校准\n2. 股票行情测试",
    title3: "灵感备忘",
    text3: "极简黑白灰，信息一目了然",
  });

  return (
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
            await onSubmit({
              memo_title_1: memoDraft.title1,
              memo_text_1: memoDraft.text1,
              memo_title_2: memoDraft.title2,
              memo_text_2: memoDraft.text2,
              memo_title_3: memoDraft.title3,
              memo_text_3: memoDraft.text3,
            });
          }}
          disabled={previewLoading}
        >
          {locale === "zh" ? "保存并预览" : "Apply"}
        </Button>
      </div>
    </div>
  );
}

// 2. RSS
export function RssConfig({
  initialUrl = "https://36kr.com/feed",
  onClose,
  onSubmit,
}: {
  initialUrl?: string;
  onClose: () => void;
  onSubmit: (override: Record<string, unknown>) => Promise<void>;
}) {
  const [rssFeedUrl, setRssFeedUrl] = useState(initialUrl);
  const [rssItemIndex, setRssItemIndex] = useState(0);
  const [rssShowImage, setRssShowImage] = useState(true);

  return (
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
        <div className="flex items-center gap-1">
          <span>文章序号：</span>
          <input
            type="number"
            min={0}
            max={10}
            value={rssItemIndex}
            onChange={(e) => setRssItemIndex(Number(e.target.value))}
            className="w-14 rounded-sm border border-ink/20 px-1.5 py-0.5 text-xs"
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
            await onSubmit({
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
  );
}

// 3. QUOTE
export function QuoteConfig({
  modeId,
  onClose,
  onSubmit,
}: {
  modeId: string;
  onClose: () => void;
  onSubmit: (override: Record<string, unknown>) => Promise<void>;
}) {
  const [quoteDraft, setQuoteDraft] = useState("");
  const [authorDraft, setAuthorDraft] = useState("");

  return (
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
            await onSubmit(quoteDraft.trim() ? { quote: quoteDraft.trim(), author: authorDraft.trim() } : {});
          }}
        >
          保存并预览
        </Button>
      </div>
    </div>
  );
}

// 4. COUNTDOWN
export function CountdownConfig({
  onClose,
  onSubmit,
}: {
  onClose: () => void;
  onSubmit: (override: Record<string, unknown>) => Promise<void>;
}) {
  const [countdownName, setCountdownName] = useState("元旦");
  const [countdownDate, setCountdownDate] = useState("2027-01-01");

  return (
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
            await onSubmit({
              countdown_events: [{ name: countdownName, date: countdownDate, type: "countdown" }],
            });
          }}
        >
          应用并预览
        </Button>
      </div>
    </div>
  );
}

// 5. HABIT
export function HabitConfig({
  onClose,
  onSubmit,
}: {
  onClose: () => void;
  onSubmit: (override: Record<string, unknown>) => Promise<void>;
}) {
  const [habitItems, setHabitItems] = useState([
    { name: "早起", done: false },
    { name: "运动", done: false },
    { name: "阅读", done: false },
  ]);

  return (
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
            await onSubmit({ habits: habitItems });
          }}
        >
          应用并预览
        </Button>
      </div>
    </div>
  );
}

// 6. LIFEBAR
export function LifebarConfig({
  onClose,
  onSubmit,
}: {
  onClose: () => void;
  onSubmit: (override: Record<string, unknown>) => Promise<void>;
}) {
  const [userAge, setUserAge] = useState(30);
  const [lifeExpectancy, setLifeExpectancy] = useState(80);

  return (
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
            await onSubmit({ user_age: userAge, life_expectancy: lifeExpectancy });
          }}
        >
          应用并预览
        </Button>
      </div>
    </div>
  );
}

// 7. WEBHOOK
export function WebhookConfig({
  onClose,
  onSubmit,
}: {
  onClose: () => void;
  onSubmit: (override: Record<string, unknown>) => Promise<void>;
}) {
  const [webhookDraft, setWebhookDraft] = useState({
    title: "家庭环境与能耗",
    primary_metric: "24.5°C",
    primary_label: "舒适客厅温度",
    item_1_value: "52% 湿度适宜",
    item_2_value: "14 μg/m³ 优",
    item_3_value: "3.8 kWh 用电正常",
  });

  return (
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
            await onSubmit(webhookDraft);
          }}
        >
          模拟并预览
        </Button>
      </div>
    </div>
  );
}

// 8. POMODORO
export function PomodoroConfig({
  locale,
  onClose,
  onSubmit,
}: {
  locale: string;
  onClose: () => void;
  onSubmit: (override: Record<string, unknown>) => Promise<void>;
}) {
  const [taskName, setTaskName] = useState("深度专注工作");
  const [durationMinutes, setDurationMinutes] = useState(25);
  const [completedCount, setCompletedCount] = useState(3);
  const [targetCount, setTargetCount] = useState(8);

  return (
    <div className="space-y-3">
      <div>
        <label className="text-xs text-ink font-semibold block mb-1">
          {locale === "zh" ? "当前专注目标：" : "Focus Task:"}
        </label>
        <input
          value={taskName}
          onChange={(e) => setTaskName(e.target.value)}
          placeholder="如 编写方案 / 算法攻坚"
          className="w-full rounded-sm border border-ink/20 px-2.5 py-1 text-xs"
        />
      </div>
      <div className="grid grid-cols-3 gap-2">
        <div>
          <label className="text-xs text-ink block mb-1">
            {locale === "zh" ? "单次时长 (分)" : "Duration"}
          </label>
          <input
            type="number"
            min={5}
            max={120}
            value={durationMinutes}
            onChange={(e) => setDurationMinutes(Number(e.target.value))}
            className="w-full rounded-sm border border-ink/20 px-2 py-1 text-xs"
          />
        </div>
        <div>
          <label className="text-xs text-ink block mb-1">
            {locale === "zh" ? "已完成轮数" : "Completed"}
          </label>
          <input
            type="number"
            min={0}
            max={20}
            value={completedCount}
            onChange={(e) => setCompletedCount(Number(e.target.value))}
            className="w-full rounded-sm border border-ink/20 px-2 py-1 text-xs"
          />
        </div>
        <div>
          <label className="text-xs text-ink block mb-1">
            {locale === "zh" ? "目标总轮数" : "Target"}
          </label>
          <input
            type="number"
            min={1}
            max={20}
            value={targetCount}
            onChange={(e) => setTargetCount(Number(e.target.value))}
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
            await onSubmit({
              task_name: taskName,
              duration_minutes: durationMinutes,
              completed_count: completedCount,
              target_count: targetCount,
            });
          }}
        >
          应用并预览
        </Button>
      </div>
    </div>
  );
}

// 9. DRINK_WATER
export function DrinkWaterConfig({
  locale,
  onClose,
  onSubmit,
}: {
  locale: string;
  onClose: () => void;
  onSubmit: (override: Record<string, unknown>) => Promise<void>;
}) {
  const [currentCups, setCurrentCups] = useState(5);
  const [targetCups, setTargetCups] = useState(8);
  const [cupVolumeMl, setCupVolumeMl] = useState(250);

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-3 gap-2">
        <div>
          <label className="text-xs text-ink block mb-1">
            {locale === "zh" ? "今日已喝杯数" : "Current Cups"}
          </label>
          <input
            type="number"
            min={0}
            max={30}
            value={currentCups}
            onChange={(e) => setCurrentCups(Number(e.target.value))}
            className="w-full rounded-sm border border-ink/20 px-2 py-1 text-xs"
          />
        </div>
        <div>
          <label className="text-xs text-ink block mb-1">
            {locale === "zh" ? "目标饮水杯数" : "Target Cups"}
          </label>
          <input
            type="number"
            min={1}
            max={30}
            value={targetCups}
            onChange={(e) => setTargetCups(Number(e.target.value))}
            className="w-full rounded-sm border border-ink/20 px-2 py-1 text-xs"
          />
        </div>
        <div>
          <label className="text-xs text-ink block mb-1">
            {locale === "zh" ? "单杯容量 (ml)" : "Cup (ml)"}
          </label>
          <input
            type="number"
            min={50}
            max={1000}
            value={cupVolumeMl}
            onChange={(e) => setCupVolumeMl(Number(e.target.value))}
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
            await onSubmit({
              current_cups: currentCups,
              target_cups: targetCups,
              cup_volume_ml: cupVolumeMl,
            });
          }}
        >
          应用并预览
        </Button>
      </div>
    </div>
  );
}
