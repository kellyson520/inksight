export type ModeCatalogItem = {
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

export type PrimaryCategory = "all" | "life" | "productivity" | "news";

// 模式到【生活 / 效率 / 资讯】一级分类的权威映射
export const MODE_PRIMARY_CATEGORY: Record<string, "life" | "productivity" | "news"> = {
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
  DRINK_WATER: "life",

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
  POMODORO: "productivity",
  SERVER_STATUS: "productivity",

  // 资讯 (News & Alerts)
  BRIEFING: "news",
  HOTLIST: "news",
  MOYU: "news",
  RSS: "news",
  CRYPTO: "news",
  MARKET: "news",
  THISDAY: "news",
  BIAS: "news",
  DISASTER_ALERT: "news",
};

export const CONFIGURABLE_MODES: Record<string, string> = {
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
  MARKET: "crypto",
  WEBHOOK: "webhook",
  MY_ADAPTIVE: "adaptive",
  POMODORO: "pomodoro",
  DRINK_WATER: "drink_water",
  SERVER_STATUS: "server_status",
};

export const HOTLIST_AVAILABLE_PLATFORMS = [
  { id: "zhihu", label: "知乎热榜", desc: "高热深度讨论" },
  { id: "weibo", label: "微博热搜", desc: "全民实时热度" },
  { id: "bilibili", label: "B站热门", desc: "热门视频与科技" },
  { id: "baidu", label: "百度热搜", desc: "全网即时事件" },
  { id: "github", label: "GitHub Trending", desc: "全球开源热门趋势" },
];

export const DISASTER_LEVELS = [
  { id: "红色", roman: "I级", label: "红色预警", desc: "特别严重 · 最高警戒" },
  { id: "橙色", roman: "II级", label: "橙色预警", desc: "严重 · 紧急防范" },
  { id: "黄色", roman: "III级", label: "黄色预警", desc: "较重 · 密切防灾" },
  { id: "蓝色", roman: "IV级", label: "蓝色预警", desc: "一般 · 注意避险" },
];

export const DISASTER_HAZARDS = [
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

export const POPULAR_STOCKS = [
  { sym: "AAPL", name: "苹果", desc: "Apple Inc." },
  { sym: "TSLA", name: "特斯拉", desc: "Tesla Inc." },
  { sym: "NVDA", name: "英伟达", desc: "NVIDIA Corp." },
  { sym: "MSFT", name: "微软", desc: "Microsoft" },
  { sym: "GOOGL", name: "谷歌", desc: "Alphabet" },
  { sym: "AMZN", name: "亚马逊", desc: "Amazon" },
  { sym: "META", name: "Meta", desc: "Meta Platforms" },
  { sym: "BABA", name: "阿里巴巴", desc: "Alibaba Group" },
];

export const POPULAR_CRYPTOS = [
  { sym: "BTC", name: "比特币", desc: "Bitcoin" },
  { sym: "ETH", name: "以太坊", desc: "Ethereum" },
  { sym: "SOL", name: "Solana", desc: "Solana" },
  { sym: "BNB", name: "币安币", desc: "BNB" },
  { sym: "DOGE", name: "狗狗币", desc: "Dogecoin" },
];

export interface SavedTickerItem {
  sym: string;
  name?: string;
  isCustom?: boolean;
}

export const STORAGE_KEY_SAVED_TICKERS = "inksight_preview_saved_tickers";
export const STORAGE_KEY_DEFAULT_TICKER = "inksight_preview_default_ticker";

export const DEFAULT_USER_SAVED_TICKERS: SavedTickerItem[] = [
  { sym: "BTC", name: "比特币" },
  { sym: "ETH", name: "以太坊" },
  { sym: "AAPL", name: "苹果" },
  { sym: "NVDA", name: "英伟达" },
];
