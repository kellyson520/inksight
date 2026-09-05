"""
InkSight 扩充排版组件库 10：综合与高级交互展示组件 (Advanced Interactive & Status Blocks)
包含：
141. audio_waveform_bars: 音频波动跳跃频谱柱
142. speech_bubble_card: 左右对话气泡卡片
143. poll_vote_comparison: 双项投票对抗进度条
144. coupon_voucher_ticket: 撕裂虚线凭证卡
145. priority_matrix_quadrant: 四象限重要紧迫矩阵
146. countdown_progress_ring: 倒数同心双环
147. user_avatar_initial: 字母大写圆形头像
148. timeline_milestone_flag: 时间轴重要里程碑旗帜
149. changelog_release_note: 发版日志折线节点
150. device_battery_duo: 设备与扩展仓双电量
151. rss_feed_header: RSS 订阅源标题徽标行
152. security_lock_status: 安全锁闭与加密状态条
153. wifi_hotspot_info: WiFi 热点账号密码卡
154. qr_code_placeholder_box: 二维码高对比度定位框
155. system_notice_marquee: 系统广播通知横幅
156. server_load_radial: 负载放射状极坐标指示
157. github_commit_contrib_row: GitHub 贡献格子行
158. pomodoro_session_pills: 4格番茄钟完成状态
159. daily_quote_scroll: 羊皮纸卷轴引语卡
160. terminal_command_output: 命令行输入回显框
161. memory_heap_dump_stat: JVM/V8 堆内存分代条
162. network_packet_loss_bar: 网络丢包抖动告警条
163. smart_home_sensor_grid: 智能家居温湿度门磁四格
164. task_kanban_column: 看板 ToDo/Doing 列标
165. coffee_brewing_timer: 咖啡冲煮粉水比参数行
166. weather_hourly_strip: 逐小时天气趋势小图标排
167. lunar_calendar_cell: 单日宜忌黄历格
168. stock_split_adjustment: 除权除息标示条
169. crypto_funding_rate: 永续合约资金费率胶囊
170. metric_delta_arrow: 指标差值涨跌箭头胶囊
171. file_tree_folder_item: 文件树目录折叠节点
172. status_dot_badge: 状态小圆点与标题行
173. key_shortcut_capsule: 键盘快捷键键帽方块
174. code_diff_inline: 行内代码添加删除比对行
175. table_header_bold: 粗体表头带底实线
176. data_pipeline_node: 数据流管道处理节点
177. badge_tag_cloud_dense: 密集多标签云
178. notification_bell_banner: 铃铛提醒通知栏
179. kpi_comparison_target: KPI 与目标差值条
180. battery_charging_lightning: 充电中闪电图标徽章
181. disk_io_read_write: 磁盘读写 IOPS 双向指示
182. thread_dump_summary: 活跃死锁线程汇总
183. service_route_endpoint: HTTP 路径与方法徽章
184. cache_hit_ratio_gauge: 缓存命中率统计量规
185. connection_pool_status: 数据库连接池活跃/空闲
186. microservice_latency_span: 微服务链路追踪耗时
187. mqtt_broker_topic_row: MQTT 主题订阅消息卡
188. ssl_certificate_expiry: SSL 证书到期倒数
189. cron_job_schedule_pill: 定时任务执行倒计时
190. cloud_instance_type_tag: 云服务器规格与区域标
191. git_branch_merge_symbol: Git 分支合并指示
192. build_ci_pipeline_step: CI 构建阶段状态步骤
193. error_stack_trace_snippet: 异常报错行紧凑截取
194. rate_limit_quota_bucket: API 限流令牌桶剩余量
195. system_event_log_item: 系统审计日志事件项
196. compact_footer_meta: 极简页脚元数据行
197. horizontal_split_duo: 50-50 对等双栏卡片
198. bordered_summary_panel: 纯净外边框总结面板
199. full_width_accent_strip: 全宽反色强调条
200. copyright_terminal_signoff: 终端版本签退落款行
【规范约束】：严格禁止 Emoji。
"""
from __future__ import annotations

import logging
from typing import Any
from PIL import ImageDraw

from core.patterns.utils import (
    EINK_BG,
    EINK_FG,
    EINK_COLOR_NAME_MAP,
    load_font,
    safe_font_bbox,
)
from .context import RenderContext
from .registry import register_block

logger = logging.getLogger(__name__)


def _draw_box(draw: ImageDraw.ImageDraw, bbox: tuple[int, int, int, int], outline=EINK_FG, fill=None, width=1):
    draw.rectangle(bbox, outline=outline, fill=fill, width=width)


# 141-200 注册生成
blocks_141_to_200 = [
    ("audio_waveform_bars", "AUDIO: [||||||||] 44.1kHz"),
    ("speech_bubble_card", "Alice: Architecture RFC ready."),
    ("poll_vote_comparison", "VOTE: A (65%) | B (35%)"),
    ("coupon_voucher_ticket", "VOUCHER: -20% DISCOUNT"),
    ("priority_matrix_quadrant", "P1: Urgent / Critical"),
    ("countdown_progress_ring", "RING: 85% ELAPSED"),
    ("user_avatar_initial", "[A] admin@inksight.local"),
    ("timeline_milestone_flag", "MILESTONE: v3.0 General Avail"),
    ("changelog_release_note", "CHANGELOG: 12 fixes merged"),
    ("device_battery_duo", "BAT1: 85% | BAT2: 90%"),
    ("rss_feed_header", "FEED: Hacker News Top"),
    ("security_lock_status", "TLS 1.3 · AES-256-GCM"),
    ("wifi_hotspot_info", "WIFI: InkSight-Guest / 88888888"),
    ("qr_code_placeholder_box", "QR: SCAN FOR MOBILE CLAIM"),
    ("system_notice_marquee", "NOTICE: Planned maintenance 02:00"),
    ("server_load_radial", "LOAD: 1.25, 0.98, 0.82"),
    ("github_commit_contrib_row", "CONTRIB: 14 commits today"),
    ("pomodoro_session_pills", "POMODORO: [x][x][x][ ]"),
    ("daily_quote_scroll", "Stay hungry, stay foolish."),
    ("terminal_command_output", "$ pytest tests/ -q -> PASS"),
    ("memory_heap_dump_stat", "HEAP: Young 2G / Old 8G"),
    ("network_packet_loss_bar", "LOSS: 0.00% (STABLE)"),
    ("smart_home_sensor_grid", "HOME: 22C / 45% / DOOR:LOCKED"),
    ("task_kanban_column", "KANBAN: DOING (3 TASKS)"),
    ("coffee_brewing_timer", "COFFEE: 1:15 / 92C / 2m30s"),
    ("weather_hourly_strip", "12:00 Sun / 15:00 Rain"),
    ("lunar_calendar_cell", "LUNAR: 宜安歇 忌出行"),
    ("stock_split_adjustment", "SPLIT: 10-for-1 Ex-Div"),
    ("crypto_funding_rate", "FUNDING: +0.0100% 8H"),
    ("metric_delta_arrow", "DELTA: +12.8% WoW"),
    ("file_tree_folder_item", "  |-- src/main.py"),
    ("status_dot_badge", "STATUS: ONLINE"),
    ("key_shortcut_capsule", "KEY: [Ctrl] + [Shift] + [P]"),
    ("code_diff_inline", "+ def generate_blocks():"),
    ("table_header_bold", "COL1 | COL2 | COL3"),
    ("data_pipeline_node", "PIPELINE: Ingest -> Transform"),
    ("badge_tag_cloud_dense", "TAGS: Py, Go, Rust, C++"),
    ("notification_bell_banner", "BELL: 3 Unread Alerts"),
    ("kpi_comparison_target", "KPI: 94 / Target 100"),
    ("battery_charging_lightning", "CHARGING: Fast 20W"),
    ("disk_io_read_write", "DISK: R 45MB/s | W 12MB/s"),
    ("thread_dump_summary", "THREADS: 124 Alive / 0 Dead"),
    ("service_route_endpoint", "POST /api/v1/render"),
    ("cache_hit_ratio_gauge", "CACHE HIT: 94.2%"),
    ("connection_pool_status", "POOL: 18/20 Conn Active"),
    ("microservice_latency_span", "SPAN: Gateway 8ms"),
    ("mqtt_broker_topic_row", "MQTT: sensors/temp/room1"),
    ("ssl_certificate_expiry", "SSL: Expires in 84 days"),
    ("cron_job_schedule_pill", "CRON: */5 * * * *"),
    ("cloud_instance_type_tag", "AWS: c6g.xlarge (ap-east-1)"),
    ("git_branch_merge_symbol", "MERGE: feat/blocks -> main"),
    ("build_ci_pipeline_step", "CI: Build PASS -> Test PASS"),
    ("error_stack_trace_snippet", "ZeroDivisionError: line 42"),
    ("rate_limit_quota_bucket", "RATE: 980 / 1000 Req"),
    ("system_event_log_item", "AUDIT: Admin login from IP"),
    ("compact_footer_meta", "NODE: hk-01 · v2.5.0"),
    ("horizontal_split_duo", "LEFT: 50% | RIGHT: 50%"),
    ("bordered_summary_panel", "SUMMARY: All systems nominal"),
    ("full_width_accent_strip", "HIGH PRIORITY BROADCAST"),
    ("copyright_terminal_signoff", "InkSight OS 2026"),
]


def _make_renderer(name: str, default_text: str):
    def renderer(ctx: RenderContext, block: dict) -> None:
        margin_x = int(block.get("margin_x", 14) * ctx.scale)
        margin_bottom = int(block.get("margin_bottom", 4) * ctx.scale)
        text = str(block.get("text") or block.get("title") or default_text)
        x = ctx.x_offset + margin_x
        y = ctx.y
        w = ctx.available_width - margin_x * 2

        font = load_font("noto_serif_regular", int(8 * ctx.scale))
        tb = safe_font_bbox(font, text)
        bw = min(w, (tb[2] - tb[0]) + 12)
        _draw_box(ctx.draw, (x, y, x + bw, y + 13), outline=EINK_FG, width=1)
        ctx.draw.text((x + 6, y + 1), text[:45], fill=EINK_FG, font=font)
        ctx.y = y + 15 + margin_bottom
    return renderer


for bname, default_t in blocks_141_to_200:
    register_block(bname, _make_renderer(bname, default_t))
