"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { LocationPicker } from "@/components/config/location-picker";
import { cleanLocationValue, type LocationValue } from "@/lib/locations";

interface WeatherConfigProps {
  initialLocation: LocationValue;
  locale: string;
  previewLoading: boolean;
  onClose: () => void;
  onSubmit: (override: Record<string, unknown>) => Promise<void>;
}

export function WeatherConfig({
  initialLocation,
  locale,
  previewLoading,
  onClose,
  onSubmit,
}: WeatherConfigProps) {
  const [draftLocation, setDraftLocation] = useState<LocationValue>(initialLocation);

  return (
    <div className="space-y-3">
      <div className="text-xs text-ink-light">
        {locale === "zh" ? "搜索并选择具体城市或地区：" : "Search and choose a specific location:"}
      </div>
      <LocationPicker
        value={draftLocation}
        onChange={setDraftLocation}
        locale={locale === "zh" ? "zh" : "en"}
        placeholder={locale === "zh" ? "输入城市名称（如：上海、北京、Tokyo）" : "Enter city name..."}
        className="w-full rounded-sm border border-ink/20 px-3 py-2 text-sm bg-white"
        autoFocus
      />
      <div className="pt-3 flex items-center justify-end gap-2 border-t border-ink/10">
        <Button
          variant="outline"
          size="sm"
          onClick={() => setDraftLocation({ city: "杭州" })}
        >
          {locale === "zh" ? "设为杭州" : "Reset"}
        </Button>
        <Button
          size="sm"
          onClick={async () => {
            const loc = cleanLocationValue(draftLocation);
            onClose();
            await onSubmit(loc.city ? (loc as Record<string, unknown>) : {});
          }}
          disabled={previewLoading}
        >
          {locale === "zh" ? "应用并预览" : "Apply"}
        </Button>
      </div>
    </div>
  );
}
