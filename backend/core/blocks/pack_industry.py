"""
InkSight 扩充排版组件库 13：工业物联网、PLC、电力能源与智能制造 (IoT & Industrial 361-410)
包含专业工厂制造与工业物联网传感器组件：
361. modbus_register_value: Modbus RTU 保持寄存器数值行
362. plc_ladder_rung_logic: PLC 梯形图常开常闭逻辑触点
363. three_phase_voltage_meter: 三相交流电压平衡表 (U/V/W)
364. industrial_boiler_psi: 工业蒸汽锅炉气压表
365. conveyor_belt_speed_rpm: 输送带变频器滚筒转速
366. hydraulic_pressure_bar: 液压泵站千帕/巴系统压力
367. cleanroom_particle_counter: 无尘洁净室微粒浓度计数 (ISO 5)
368. solar_inverter_efficiency: 光伏逆变器 MPPT 转换效率
369. wind_turbine_pitch_angle: 风力发电机叶片变桨迎风角
370. transformer_oil_temperature: 变压器绝缘油顶层油温
371. relay_coil_energized_state: 继电器线圈吸合带电指示
372. gas_leak_ppm_sensor: 可燃气体/甲烷 PPM 浓度告警
373. vibration_piezo_rms: 旋转电机压电振动加速度有效值
374. pneumatic_valve_position: 气动调节阀开度百分比 (4-20mA)
375. grid_frequency_hertz: 国家电网交流基波工频 (50.00Hz)
376. diesel_generator_fuel_level: 应急柴油发电机储油罐液位
377. wastewater_ph_probe: 工业废水在线 pH 酸碱度计
378. welding_current_amperage: 自动化机器人弧焊电流电压
379. scada_alarm_severity_tag: SCADA 工业告警等级标识
380. canbus_packet_rate_gauge: 车载/工业 CAN 总线吞吐帧率
381. ups_battery_backup_runtime: 机房工业 UPS 延时备电分钟
382. smt_nozzle_pick_rate_cph: SMT 贴片机每小时贴装元件速度
383. laser_cutting_head_power: 光纤激光切割头实时出光功率
384. cnc_spindle_load_percent: CNC 数控机床主轴负载率
385. water_cooling_chiller_flow: 工业冷水机冷却水循环流量
386. exhaust_stack_opacity_smoke: 工业烟囱脱硫排放林格曼黑度
387. power_factor_cos_phi: 变电所电能质量功率因数 (Cos Phi)
388. radiation_portal_monitor: 港口放射性门式监测通过报警
389. automated_guided_vehicle_agv: AGV 搬运小车导航电池与工位
390. packaging_line_oee_score: 包装产线综合设备效率 (OEE)
391. torque_wrench_calibration: 扭矩扳手螺栓拧紧牛米扭矩
392. cryogenic_nitrogen_tank_lvl: 深冷液氮绝热储罐液位计
393. clean_room_differential_pa: 洁净室正负压微压差 (Pa)
394. harmonic_distortion_thd_pct: 电网总谐波电压畸变率 (THD)
395. oil_pipeline_scada_valve: 原油长输管线紧急截断阀状态
396. batch_reactor_agitation_rpm: 化工反应釜搅拌锚式桨转速
397. clean_steam_conductivity: 洁净蒸汽电导率超纯水电导
398. sil_safety_integrity_level: 功能安全完整性等级徽章 (SIL 3)
399. thermal_imaging_hotspot_deg: 红外热成像最高局部过热温升
400. emergency_stop_circuit_loop: 物理急停双回路常闭导通监控
401. silo_grain_storage_tonnage: 粮仓粉料重力称重筒仓吨位
402. dust_explosion_risk_lel: 易燃粉尘爆炸下限风险浓度
403. blast_furnace_top_pressure: 钢铁高炉炉顶煤气压差
404. centrifugal_pump_cavitation: 离心泵气蚀汽蚀振动频谱指示
405. smart_grid_meter_kwh_daily: 智能电表日累积有功电量
406. variable_frequency_drive_hz: 变频器当前输出调速频率 (Hz)
407. safety_light_curtain_optical: 冲压机床安全红外光栅保护区
408. cooling_tower_fan_vibration: 循环水冷却塔风机振动超限
409. gas_turbine_exhaust_temp: 燃气轮机透平排气均温 (EGT)
410. production_shift_yield_rate: 制造车间当班合格率直通率 (FPY)
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


industry_blocks_361_410 = [
    ("modbus_register_value", "MODBUS: 40001 = 0x4A2F (Val: 18991)"),
    ("plc_ladder_rung_logic", "LADDER: --[ I0.0 ]--[/ M0.1 ]--( Q0.0 )-"),
    ("three_phase_voltage_meter", "3-PHASE: U:380V V:381V W:379V (BAL)"),
    ("industrial_boiler_psi", "BOILER: Steam 1.42 MPa (206 PSI)"),
    ("conveyor_belt_speed_rpm", "CONVEYOR: VFD 1,450 RPM (1.2 m/s)"),
    ("hydraulic_pressure_bar", "HYDRAULIC: Pump 210 bar (Nominal)"),
    ("cleanroom_particle_counter", "CLEANROOM: 0.5um = 280 /ft3 (ISO 5)"),
    ("solar_inverter_efficiency", "SOLAR: Inverter Eff 98.6% (12.4 kW)"),
    ("wind_turbine_pitch_angle", "TURBINE: Pitch 14.2 deg (Wind 8.4m/s)"),
    ("transformer_oil_temperature", "XFRMR: Top Oil 62.4C (Max 85C)"),
    ("relay_coil_energized_state", "RELAY: K1 ENERGIZED · 24VDC"),
    ("gas_leak_ppm_sensor", "GAS: CH4 0.0 ppm (Safe Threshold)"),
    ("vibration_piezo_rms", "VIBE: Motor RMS 2.1 mm/s (Class A)"),
    ("pneumatic_valve_position", "VALVE: FC01 Pos 65.4% (4-20mA)"),
    ("grid_frequency_hertz", "GRID: 50.002 Hz (Stable Sync)"),
    ("diesel_generator_fuel_level", "GENSET: Fuel 84% (Runtime 32h)"),
    ("wastewater_ph_probe", "WATER: pH 7.24 (Conductivity 140uS)"),
    ("welding_current_amperage", "WELD: 180A / 22.4V (Wire 1.2mm)"),
    ("scada_alarm_severity_tag", "SCADA: Priority 1 Major Alarm ACK"),
    ("canbus_packet_rate_gauge", "CAN: 250 kbps · Load 34.2% (No Err)"),
    ("ups_battery_backup_runtime", "UPS: Load 48% (Battery Est 45m)"),
    ("smt_nozzle_pick_rate_cph", "SMT: 42,000 CPH · Feeder OK"),
    ("laser_cutting_head_power", "LASER: Output 6,000 W (N2 Assist)"),
    ("cnc_spindle_load_percent", "CNC: Spindle 12,000 RPM (Load 48%)"),
    ("water_cooling_chiller_flow", "CHILLER: Supply 14.0C (Flow 45L/m)"),
    ("exhaust_stack_opacity_smoke", "STACK: Ringelmann 0.2 (SO2 12mg)"),
    ("power_factor_cos_phi", "PF: Cos Phi 0.96 (Capacitor ON)"),
    ("radiation_portal_monitor", "PORTAL: Gate 02 Clean (0.12 uSv/h)"),
    ("automated_guided_vehicle_agv", "AGV-04: Battery 78% · Station B3"),
    ("packaging_line_oee_score", "OEE: 88.4% (Avail 94% Perf 94%)"),
    ("torque_wrench_calibration", "TORQUE: 45.2 Nm (Spec 45+/-2)"),
    ("cryogenic_nitrogen_tank_lvl", "LN2: Tank 72% (Pressure 0.8 MPa)"),
    ("clean_room_differential_pa", "DP: Room 102 +25.4 Pa (Positive)"),
    ("harmonic_distortion_thd_pct", "THD: Voltage 1.8% (IEEE 519 Pass)"),
    ("oil_pipeline_scada_valve", "PIPELINE: Block Valve 14 OPEN"),
    ("batch_reactor_agitation_rpm", "REACTOR: Agitator 120 RPM (Temp 85C)"),
    ("clean_steam_conductivity", "STEAM: Cond 0.82 uS/cm (Pure)"),
    ("sil_safety_integrity_level", "SAFETY: Functional Safety SIL 3"),
    ("thermal_imaging_hotspot_deg", "THERMAL: Max 48.2C (Delta +12C)"),
    ("emergency_stop_circuit_loop", "E-STOP: Dual Loop Closed Healthy"),
    ("silo_grain_storage_tonnage", "SILO: Load Cell 428.5 Tons (85%)"),
    ("dust_explosion_risk_lel", "DUST: LEL 4.2% (Below Threshold)"),
    ("blast_furnace_top_pressure", "FURNACE: Top Press 240 kPa (Stable)"),
    ("centrifugal_pump_cavitation", "PUMP: Suction 0.4MPa No Cavitation"),
    ("smart_grid_meter_kwh_daily", "METER: Today Active 2,840 kWh"),
    ("variable_frequency_drive_hz", "VFD: Output 48.5 Hz (Bus 540V)"),
    ("safety_light_curtain_optical", "CURTAIN: Optical Beam Unbroken"),
    ("cooling_tower_fan_vibration", "TOWER: Fan Vibration 1.4 mm/s"),
    ("gas_turbine_exhaust_temp", "TURBINE: EGT 542C (Spread 14C)"),
    ("production_shift_yield_rate", "FPY: First Pass Yield 99.4%"),
]


def _make_industry_renderer(bname: str, default_text: str):
    def renderer(ctx: RenderContext, block: dict) -> None:
        margin_x = int(block.get("margin_x", 14) * ctx.scale)
        margin_bottom = int(block.get("margin_bottom", 4) * ctx.scale)
        text = str(block.get("text") or block.get("title") or default_text)
        x = ctx.x_offset + margin_x
        y = ctx.y
        w = ctx.available_width - margin_x * 2

        # 工业工控粗犷双线边框
        _draw_box(ctx.draw, (x, y, x + w, y + 14), outline=EINK_FG, width=1)
        _draw_box(ctx.draw, (x + 2, y + 2, x + 6, y + 12), fill=EINK_FG)
        font = load_font("noto_serif_regular", int(8 * ctx.scale))
        ctx.draw.text((x + 10, y + 1), text[:52], fill=EINK_FG, font=font)
        ctx.y = y + 16 + margin_bottom
    return renderer


for bname, bdesc in industry_blocks_361_410:
    register_block(bname, _make_industry_renderer(bname, bdesc))
