"""
Shared pytest fixtures for InkSight unit tests.
"""
import os
import subprocess
import sys
from pathlib import Path

import pytest

# Ensure backend root is on sys.path so `core.*` imports work
BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

# Set dummy env vars so modules can import without real keys
os.environ.setdefault("DEEPSEEK_API_KEY", "sk-test-dummy-key-000")
os.environ.setdefault("DASHSCOPE_API_KEY", "sk-test-dummy-key-001")
os.environ.setdefault("MOONSHOT_API_KEY", "sk-test-dummy-key-002")


def pytest_sessionstart(session):
    """Build the native dithering library before tests import renderers."""
    native_lib = BACKEND_ROOT / "core" / "native" / "libeink_dither.so"
    if native_lib.exists():
        return
    script = BACKEND_ROOT / "scripts" / "build_native_dither.py"
    subprocess.run([sys.executable, str(script)], cwd=BACKEND_ROOT, check=True)


def _close_databases_sync():
    """Wait for shared aiosqlite workers to close before pytest exits."""
    import asyncio
    from core.db import close_all

    try:
        running_loop = asyncio.get_running_loop()
    except RuntimeError:
        running_loop = None

    if running_loop and running_loop.is_running():
        import threading
        error = []

        def close_in_thread():
            try:
                asyncio.run(close_all())
            except Exception as exc:
                error.append(exc)

        thread = threading.Thread(target=close_in_thread, name="pytest-db-cleanup")
        thread.start()
        thread.join(timeout=15)
        if error:
            raise error[0]
        return

    asyncio.run(close_all())


def pytest_sessionfinish(session, exitstatus):
    """Clean up open database connections before pytest completes."""
    try:
        _close_databases_sync()
    except Exception:
        pass


@pytest.fixture(autouse=True)
def isolate_persistent_interceptors():
    """Prevent durable alert state from leaking between tests."""
    yield
    try:
        from core.monitor_service import monitor_service
        monitor_service.clear_notices()
    except Exception:
        pass
    try:
        from core import disaster_service
        disaster_service._SIMULATED_ALERTS.clear()
        disaster_service._ALERT_CACHE.clear()
    except Exception:
        pass


@pytest.fixture
def sample_config():
    """A typical device configuration dict."""
    return {
        "mac": "AA:BB:CC:DD:EE:FF",
        "nickname": "TestDevice",
        "modes": ["STOIC", "ROAST", "ZEN"],
        "refresh_strategy": "cycle",
        "refresh_interval": 60,
        "character_tones": [],
        "language": "zh",
        "content_tone": "neutral",
        "city": "杭州",
        "llm_provider": "deepseek",
        "llm_model": "deepseek-chat",
    }


@pytest.fixture
def sample_date_ctx():
    """A typical date context dict."""
    return {
        "date_str": "2月16日 周一",
        "time_str": "09:30:00",
        "weekday": 0,
        "hour": 9,
        "is_weekend": False,
        "year": 2026,
        "day": 16,
        "month_cn": "二月",
        "weekday_cn": "周一",
        "day_of_year": 47,
        "days_in_year": 365,
        "festival": "",
        "is_holiday": False,
        "is_workday": True,
        "upcoming_holiday": "清明节",
        "days_until_holiday": 48,
        "holiday_date": "04月05日",
        "daily_word": "春风化雨",
    }


@pytest.fixture
def sample_weather():
    """A typical weather dict."""
    return {
        "temp": 12,
        "weather_code": 1,
        "weather_str": "12°C",
    }
