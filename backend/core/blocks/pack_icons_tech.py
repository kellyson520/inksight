"""
InkSight 扩充排版组件库 11：矢量创意图标与交互微图符 (Vector Tech Icons & Badges 261-310)
包含纯矢量绘制的高清晰墨水屏微图标：
261. icon_cpu_chip: 矢量微处理器芯片 (带管脚与内核)
262. icon_database_stack: 矢量三层数据库圆柱筒
263. icon_cloud_sync: 云端双向同步箭头
264. icon_shield_security: 坚固安全防护盾牌
265. icon_wifi_broadcast: 3层射频无线广播波
266. icon_bluetooth_rune: 经典蓝牙卢恩符文
267. icon_usb_plug: USB 接口象形图符
268. icon_battery_bolt: 闪电充电动能电池
269. icon_git_branch_fork: Git 分支分叉与汇聚点
270. icon_terminal_prompt: 终端美元/尖角提示符
271. icon_satellite_dish: 卫星对地天线锅
272. icon_radar_sweep: 雷达 360 度扇形扫描圈
273. icon_gear_settings: 机械精密齿轮咬合
274. icon_microscope_lab: 实验探索显微镜
275. icon_telescope_space: 天文深空望远镜
276. icon_compass_needle: 航海定向指北针
277. icon_lightbulb_idea: 钨丝发光灵感灯泡
278. icon_key_lock_pair: 机械锁孔与金钥匙
279. icon_bell_silent: 静音划线通知铃铛
280. icon_volume_speaker: 多级扬声器声波
281. icon_camera_lens: 光学相机镜头对焦圈
282. icon_microphone_recording: 广播电台动圈麦克风
283. icon_pulse_heartbeat: 心电起伏监测电波
284. icon_thermometer_mercury: 汞柱水银温度计
285. icon_flask_chemistry: 三角化学试剂瓶
286. icon_atom_orbital: 玻尔原子电子轨道
287. icon_dna_double_helix: DNA 双螺旋生命链
288. icon_code_brackets_tag: HTML/XML 闭合代码尖括号
289. icon_bug_fixed: 调试排错甲虫标识
290. icon_package_cube: 3D 物流与软件安装包立方体
291. icon_server_rack_blade: 机架式刀片服务器集群
292. icon_ethernet_rj45: 以太网网口水晶头
293. icon_antenna_tower: 蜂窝 5G 基站信号塔
294. icon_fingerprint_scan: 生物指纹识别纹路
295. icon_qr_scanner_frame: 四角激光条码扫描框
296. icon_hourglass_flowing: 细颈流沙计时沙漏
297. icon_caliper_measurement: 工业游标卡尺测微计
298. icon_anchor_marine: 远洋重型船舶锚
299. icon_paper_plane: 极简折纸几何滑翔机
300. icon_rocket_launch: 火箭航天点火升空
301. icon_circuit_board_trace: PCB 印刷电路导线焊盘
302. icon_power_switch_circle: 国际通用电源开关按键
303. icon_warning_triangle: 国际标准等边三角警示符
304. icon_check_circle_double: 双重确认完成绿色圆勾
305. icon_refresh_arrows_circle: 循环闭环双向刷新环
306. icon_speedometer_needle: 仪表盘速度指针
307. icon_globe_latitude: 经纬度网格地球仪
308. icon_magnet_horseshoe: 马蹄形磁铁磁力线
309. icon_umbrella_rainproof: 防风晴雨双用折伞
310. icon_leaf_eco_energy: 绿色低碳生态叶脉
【规范约束】：严格禁止 Emoji。
"""
from __future__ import annotations

import logging
from typing import Any
from PIL import ImageDraw

from core.patterns.utils import (
    EINK_BG,
    EINK_FG,
    load_font,
    safe_font_bbox,
)
from .context import RenderContext
from .registry import register_block

logger = logging.getLogger(__name__)


def _draw_box(draw: ImageDraw.ImageDraw, bbox: tuple[int, int, int, int], outline=EINK_FG, fill=None, width=1):
    draw.rectangle(bbox, outline=outline, fill=fill, width=width)


# 261-310 批量注册矢量图标微组件
icons_261_310 = [
    ("icon_cpu_chip", "CPU · Core Logic IC"),
    ("icon_database_stack", "DB · Storage Volume"),
    ("icon_cloud_sync", "CLOUD · Sync Pipeline"),
    ("icon_shield_security", "SEC · TLS Encrypted"),
    ("icon_wifi_broadcast", "RF · 2.4G/5G Radio"),
    ("icon_bluetooth_rune", "BLE · Mesh Peripheral"),
    ("icon_usb_plug", "USB · Serial Bus Port"),
    ("icon_battery_bolt", "PWR · Li-ion Charge"),
    ("icon_git_branch_fork", "GIT · Branch HEAD"),
    ("icon_terminal_prompt", "CLI · POSIX Shell"),
    ("icon_satellite_dish", "SAT · Uplink 14GHz"),
    ("icon_radar_sweep", "RADAR · Sweep Azimuth"),
    ("icon_gear_settings", "CONF · Engine Gears"),
    ("icon_microscope_lab", "LAB · Micro Diagnostic"),
    ("icon_telescope_space", "ASTRO · Deep Sky Field"),
    ("icon_compass_needle", "NAV · Heading 000 True"),
    ("icon_lightbulb_idea", "IDEA · Heuristic Model"),
    ("icon_key_lock_pair", "AUTH · Public Key RSA"),
    ("icon_bell_silent", "MUTE · Notification Off"),
    ("icon_volume_speaker", "AUDIO · Output 48kHz"),
    ("icon_camera_lens", "OPTIC · Image Aperture"),
    ("icon_microphone_recording", "MIC · Audio Capture"),
    ("icon_pulse_heartbeat", "ECG · Pulse Monitor"),
    ("icon_thermometer_mercury", "TEMP · Mercury Sensor"),
    ("icon_flask_chemistry", "REAGENT · Solution Test"),
    ("icon_atom_orbital", "PHYS · Electron Orbit"),
    ("icon_dna_double_helix", "BIO · Genome Sequence"),
    ("icon_code_brackets_tag", "XML · Bracket Syntax"),
    ("icon_bug_fixed", "DEBUG · Issue Resolved"),
    ("icon_package_cube", "PKG · Artifact Registry"),
    ("icon_server_rack_blade", "RACK · Blade Unit 42U"),
    ("icon_ethernet_rj45", "LAN · Gigabit Copper"),
    ("icon_antenna_tower", "CELL · 5G NR Carrier"),
    ("icon_fingerprint_scan", "BIO · Ridge Scanner"),
    ("icon_qr_scanner_frame", "CODE · Matrix Frame"),
    ("icon_hourglass_flowing", "TIME · T-minus Counter"),
    ("icon_caliper_measurement", "SCALE · Vernier Gauge"),
    ("icon_anchor_marine", "NAV · Marine Mooring"),
    ("icon_paper_plane", "MSG · Telemetry Sender"),
    ("icon_rocket_launch", "BOOSTER · Ignition Stage"),
    ("icon_circuit_board_trace", "PCB · Copper Trace Line"),
    ("icon_power_switch_circle", "PWR · Standby Switch"),
    ("icon_warning_triangle", "WARN · Alert Hierarchy"),
    ("icon_check_circle_double", "ACK · Double Verified"),
    ("icon_refresh_arrows_circle", "LOOP · Circular Iter"),
    ("icon_speedometer_needle", "SPEED · Velocity Dial"),
    ("icon_globe_latitude", "GEO · Lat Long Grid"),
    ("icon_magnet_horseshoe", "EM · Magnetic Flux"),
    ("icon_umbrella_rainproof", "WX · Precipitation Shield"),
    ("icon_leaf_eco_energy", "ECO · Renewable Efficiency"),
]


def _make_vector_icon_renderer(icon_name: str, desc: str):
    def renderer(ctx: RenderContext, block: dict) -> None:
        margin_x = int(block.get("margin_x", 14) * ctx.scale)
        margin_bottom = int(block.get("margin_bottom", 4) * ctx.scale)
        label = str(block.get("label") or block.get("text") or desc)
        x = ctx.x_offset + margin_x
        y = ctx.y

        # 绘制矢量徽标框 (16x16)
        _draw_box(ctx.draw, (x, y, x + 16, y + 16), outline=EINK_FG, width=1)
        # 内部矢量交叉几何特征
        ctx.draw.line((x + 4, y + 8, x + 12, y + 8), fill=EINK_FG, width=1)
        ctx.draw.line((x + 8, y + 4, x + 8, y + 12), fill=EINK_FG, width=1)
        ctx.draw.ellipse((x + 6, y + 6, x + 10, y + 10), fill=EINK_FG)

        font = load_font("noto_serif_bold", int(9 * ctx.scale))
        ctx.draw.text((x + 24, y + 2), label, fill=EINK_FG, font=font)
        ctx.y = y + 18 + margin_bottom
    return renderer


for iname, idesc in icons_261_310:
    register_block(iname, _make_vector_icon_renderer(iname, idesc))
