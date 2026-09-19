"""
测试墨水屏服务端智能动态休眠调度器 (Dynamic Sleep Scheduler)
"""
from datetime import datetime
import pytest
from core.sleep_scheduler import calculate_optimal_sleep_minutes


def test_base_interval_defaults():
    config = {"refresh_interval": 30}
    # 平常白天 (周三中午 12:00) 普通模式
    dt = datetime(2025, 5, 21, 12, 0)
    minutes = calculate_optimal_sleep_minutes(config, current_mode="DAILY", now=dt)
    assert minutes == 30


def test_night_time_power_saving():
    config = {"refresh_interval": 30}
    # 凌晨 2:30
    dt = datetime(2025, 5, 21, 2, 30)
    minutes = calculate_optimal_sleep_minutes(config, current_mode="DAILY", now=dt)
    # 夜间自动拉长休眠时间至 120 分钟以上，节省无效耗电
    assert minutes >= 120


def test_low_battery_protection():
    config = {"refresh_interval": 20}
    dt = datetime(2025, 5, 21, 14, 0)
    # 电量仅剩 10%
    minutes = calculate_optimal_sleep_minutes(config, current_mode="DAILY", now=dt, battery_pct=10.0)
    assert minutes >= 90


def test_market_hours_acceleration():
    config = {"refresh_interval": 30}
    # 周三上午 10:00 (A股/港股开盘交易时段)
    dt = datetime(2025, 5, 21, 10, 0)
    minutes = calculate_optimal_sleep_minutes(config, current_mode="MARKET_GLOBAL", now=dt)
    # 交易时段提频至 10~15 分钟
    assert minutes <= 15


def test_market_closed_on_weekend():
    config = {"refresh_interval": 15}
    # 周六下午 (休市)
    dt = datetime(2025, 5, 24, 14, 0)
    minutes = calculate_optimal_sleep_minutes(config, current_mode="MARKET_GLOBAL", now=dt)
    # 周末闭市延长休眠
    assert minutes >= 60
