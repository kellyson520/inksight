# 2026-09-04 墨水屏全网热榜拓展、防误判灾害预警、MindReset Studio 规范与统一管理界面设计

## 1. 目标
拓展更多高价值、好看样式的实用模块，并彻底统一墨水屏全平台视觉与交互架构：
1. **热榜矩阵拓展**：
   - 增加**网易云热歌榜**（`netease`，含曲名、歌手与音符徽标）、**豆瓣电影热榜**（`douban`，含电影名、豆瓣星级评分 `★ 8.2`）、**微信热榜**（`wechat`，热议话题/爆款文章与热度）、**抖音热榜**（`douyin`，短视频热词与观看热度）。
   - 升级 `hotlist_board` 布局预设，针对音乐、电影评分、社交热搜提供特色排版与指示图标。
2. **灾害预警精准地区配置与防跨区误判**：
   - 在设备配置与预览弹窗中提供地区/城市直接设置（如指定“北京市”或精确经纬度）。
   - 预警过滤器仅匹配该设备所在省/市的预警，过滤掉无关全国性或跨省警报，杜绝远距离误触发全屏避险。
3. **MindReset Studio 模块化规范引入**：
   - 遵循 `dot.mindreset.tech/docs/service/studio` 规范，按生活（Life）、效率（Productivity）、资讯（News/Feeds）、艺术/创作（Studio/Art）进行标准化模块声明。
   - 提供组件分类、数据源协议、预览属性元信息。
4. **设备管理页面风格大一统**：
   - 将现有复杂冗长的设备配置页重构为与“无设备预览页（Demo）”一致的高信息密度现代设计：
     - 左侧：分类组件选择器（网易云、豆瓣、微信、灾害预警、时钟天气、每日一词等卡片式即点即选，包含一键添加至当前设备循环）。
     - 右侧：固定墨水屏高精度实时虚拟渲染画布（支持尺寸、颜色、刷新策略即时交互）。
     - 顶部：设备状态、昵称、在线状态、快速保存与同步栏。
     - 彻底消除两套页面体验割裂感，统一视觉美学。

## 2. 接口与核心数据流
- `HotlistService`:
  - 支持 `netease` (网易云音乐云音乐热歌榜 `https://music.163.com/api/playlist/detail?id=3778678`)
  - 支持 `douban` (豆瓣电影最新热门榜单 `https://movie.douban.com/j/search_subjects?type=movie&tag=%E7%83%AD%E9%97%A8`)
  - 支持 `wechat` (微信公号及微信指数热议榜)
  - 支持 `douyin` (抖音实时热点榜 `https://aweme.snssdk.com/aweme/v1/hot/search/list/`)
- `check_device_disaster_alert`:
  - 增加 `target_city` 严格校验与归属地匹配，距离校验（阈值 120km），避免全国警报误投。
- Web 界面:
  - `webapp/app/config/page.tsx` 采用与 `webapp/app/preview/page.tsx` 相同的两栏响应式布局（`grid-cols-1 lg:grid-cols-[1fr_480px]`），整合设备模式管理与即时 E-Ink 渲染。
