"""
InkSight 扩充排版组件库 12：太空天体、深空探测与航天遥测组件 (Space & Astrometry 311-360)
包含墨水屏高清晰深空科学排版组件：
311. orbit_ellipse_schematic: 卫星椭圆轨道近地点/远地点图
312. saturn_ring_diagram: 土星光环倾角横截面
313. solar_eclipse_corona: 日全食日冕贝利珠月影图
314. mars_rover_sol_counter: 火星漫游车火星日计数器
315. deep_space_telemetry_bar: 深空探测器下行信噪比条
316. constellation_star_map: 猎户座连线星座微星图
317. lagrange_points_map: 日地拉格朗日 L1-L5 分布图
318. solar_wind_particle_gauge: 太阳风带电粒子流速量规
319. lunar_lander_altitude_tape: 登月舱动力下降高度标尺
320. exoplanet_transit_dip: 系外行星凌日光变曲线槽
321. pulsar_frequency_pulse: 脉冲星超高精度周期信号
322. cosmic_ray_detector_hit: 宇宙射线重离子撞击指示
323. radio_telescope_interferometry: 甚长基线射电干涉阵列基线
324. orbital_decay_lifetime: 低轨空间碎片轨道寿命衰减
325. aurora_oval_latitude: 极光卵带南下扩散纬度条
326. space_station_docking_target: 空间站交会对接十字瞄准线
327. solar_panel_sun_tracker: 光伏帆板对日定向倾斜角
328. reaction_wheel_rpm: 卫星姿控飞轮转速与动量矩
329. hydrazine_fuel_tank_pct: 联氨推进剂储箱剩余压力
330. ion_thruster_beam_status: 霍尔电推进离子束流发射状态
331. space_radiation_dosimeter: 舱外空间辐射累积剂量
332. meteorite_trajectory_vector: 陨石再入双曲面轨迹矢量
333. geostationary_slot_longitude: 地球静止轨道东经定点经度
334. sunspot_magnetic_group: 太阳黑子群磁极复合分类
335. doppler_shift_spectroscopy: 恒星光谱红移蓝移指示
336. escape_velocity_indicator: 第二宇宙速度逃逸比
337. atmospheric_entry_blackout: 黑障区等离子鞘套温度
338. space_debris_conjunction_risk: 空间碰撞交会预警距离
339. star_tracker_quaternion: 星敏感器姿态四元数解算
340. optical_laser_comm_link: 空间相干激光卫星链路
341. lunar_phase_illumination_pct: 月面受光照百分比曲线
342. gravity_assist_delta_v: 行星引力弹弓加速增量
343. asteroid_albedo_reflectance: 近地小行星几何反照率
344. magnetosphere_bow_shock: 地球磁层顶弓形激波距离
345. space_suit_eva_oxygen_bar: 航天服舱外活动氧气分压
346. launch_azimuth_angle: 运载火箭发射轨道射向角
347. orbital_inclination_degrees: 极地轨道轨道倾角仪表
348. perigee_burn_countdown: 近地点变轨点火倒计时
349. cryo_propellant_boil_off: 低温液氢液氧蒸发损失率
350. heat_shield_ablation_depth: 防热大底烧蚀深度监测
351. cosmic_microwave_background: 微波背景辐射各向异性
352. brown_dwarf_spectral_type: 褐矮星光谱分类徽章
353. kuiper_belt_perihelion_dist: 柯伊伯带天体近日点距离
354. solar_cycle_sunspot_number: 太阳活动周黑子数周期
355. payload_bay_temperature: 货运飞船载荷舱均温
356. retro_rocket_thrust_vector: 反推制动火箭推力矢量
357. rendezvous_radar_range_rate: 相对交会雷达测距测速
358. interplanetary_transit_days: 行星际霍曼转移轨道天数
359. solar_flux_unit_f107: 太阳 10.7cm 射电通量指标
360. mission_elapsed_time_clock: 航天任务飞行任务总时间 (MET)
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


space_blocks_311_360 = [
    ("orbit_ellipse_schematic", "ORBIT: 420x415km · Inc 41.5 deg"),
    ("saturn_ring_diagram", "RING: A/B Ring Cassini Div"),
    ("solar_eclipse_corona", "ECLIPSE: Totality 4m12s Corona"),
    ("mars_rover_sol_counter", "MARS: Sol 842 · Perseverance"),
    ("deep_space_telemetry_bar", "DSN: Canberra 70m · SNR +14dB"),
    ("constellation_star_map", "MAP: Orion Alpha Betelgeuse"),
    ("lagrange_points_map", "L-POINT: Sun-Earth L2 (JWST)"),
    ("solar_wind_particle_gauge", "WIND: 462 km/s · 6.2 p/cm3"),
    ("lunar_lander_altitude_tape", "ALT: 1,240m · Rate -12.4 m/s"),
    ("exoplanet_transit_dip", "TRANSIT: Dip 1.2% (Kepler-452b)"),
    ("pulsar_frequency_pulse", "PULSAR: B1919+21 P=1.337s"),
    ("cosmic_ray_detector_hit", "RAY: 142 TeV Proton Event"),
    ("radio_telescope_interferometry", "VLBI: 8,400km Baseline Event"),
    ("orbital_decay_lifetime", "DECAY: Estimated 480 Days"),
    ("aurora_oval_latitude", "AURORA: Kp 6.2 · Lat 58N"),
    ("space_station_docking_target", "DOCKING: Range 42m Rate 0.1m/s"),
    ("solar_panel_sun_tracker", "ARRAY: Alpha/Beta Sun Lock"),
    ("reaction_wheel_rpm", "WHEEL: 3,420 RPM (4.2 Nms)"),
    ("hydrazine_fuel_tank_pct", "FUEL: N2H4 68.4% (1.8 MPa)"),
    ("ion_thruster_beam_status", "HALL: Xenon Beam 85 mN"),
    ("space_radiation_dosimeter", "RAD: 0.42 mSv/day (Nominal)"),
    ("meteorite_trajectory_vector", "ENTRY: V=18.4 km/s Dec 42deg"),
    ("geostationary_slot_longitude", "GEO: 105.5E Station Kept"),
    ("sunspot_magnetic_group", "SUNSPOT: AR3664 Beta-Gamma-Delta"),
    ("doppler_shift_spectroscopy", "DOPPLER: z=0.042 (Radial +12km/s)"),
    ("escape_velocity_indicator", "ESCAPE: 11.186 km/s (Earth v2)"),
    ("atmospheric_entry_blackout", "PLASMA: Blackout Phase 3m20s"),
    ("space_debris_conjunction_risk", "RISK: Dist 240m Prob 1e-4"),
    ("star_tracker_quaternion", "ATT: q0=0.707 q1=0 q2=0.707"),
    ("optical_laser_comm_link", "LASER: 1.24 Gbps Moon-to-Ground"),
    ("lunar_phase_illumination_pct", "MOON: 94.2% Waxing Gibbous"),
    ("gravity_assist_delta_v", "FLYBY: Jupiter Delta-V +4.8km/s"),
    ("asteroid_albedo_reflectance", "ALBEDO: 0.14 Type-C Asteroid"),
    ("magnetosphere_bow_shock", "SHOCK: Bow Shock 10.4 Re"),
    ("space_suit_eva_oxygen_bar", "EMU: O2 Pressure 29.6 kPa"),
    ("launch_azimuth_angle", "AZIMUTH: 092.4 Deg East"),
    ("orbital_inclination_degrees", "INC: 98.2 Deg Sun-Sync"),
    ("perigee_burn_countdown", "BURN: T-00:14:22 DeltaV 420m/s"),
    ("cryo_propellant_boil_off", "CRYO: LH2/LOX Vent 0.02%/hr"),
    ("heat_shield_ablation_depth", "SHIELD: PICA-X 12.4mm Left"),
    ("cosmic_microwave_background", "CMB: 2.7255 K Blackbody"),
    ("brown_dwarf_spectral_type", "DWARF: Spectral Class T6"),
    ("kuiper_belt_perihelion_dist", "KBO: Perihelion 38.4 AU"),
    ("solar_cycle_sunspot_number", "CYCLE: Cycle 25 SSN 148"),
    ("payload_bay_temperature", "BAY: Temp +18.4C Stable"),
    ("retro_rocket_thrust_vector", "RETRO: F=4x400N Pitch 0"),
    ("rendezvous_radar_range_rate", "R-RADAR: 480m (-1.2m/s)"),
    ("interplanetary_transit_days", "TRANSIT: Mars Cruise Day 142"),
    ("solar_flux_unit_f107", "FLUX: F10.7 = 184 sfu"),
    ("mission_elapsed_time_clock", "MET: 042:18:24:50"),
]


def _make_space_renderer(bname: str, default_text: str):
    def renderer(ctx: RenderContext, block: dict) -> None:
        margin_x = int(block.get("margin_x", 14) * ctx.scale)
        margin_bottom = int(block.get("margin_bottom", 4) * ctx.scale)
        text = str(block.get("text") or block.get("title") or default_text)
        x = ctx.x_offset + margin_x
        y = ctx.y
        w = ctx.available_width - margin_x * 2

        # 航天风格外框与角标装饰
        _draw_box(ctx.draw, (x, y, x + w, y + 14), outline=EINK_FG, width=1)
        # 左侧航天科技细线
        ctx.draw.line((x + 4, y + 2, x + 4, y + 12), fill=EINK_FG, width=2)
        font = load_font("noto_serif_regular", int(8 * ctx.scale))
        ctx.draw.text((x + 10, y + 1), text[:50], fill=EINK_FG, font=font)
        ctx.y = y + 16 + margin_bottom
    return renderer


for bname, bdesc in space_blocks_311_360:
    register_block(bname, _make_space_renderer(bname, bdesc))
