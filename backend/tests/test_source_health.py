import time
import pytest
from core.source_health import SourceHealthRegistry, SourceState


def test_source_health_initially_healthy():
    registry = SourceHealthRegistry(failure_threshold=3, cooldown_seconds=10)
    assert registry.should_allow_request("weibo") is True
    status = registry.get_status("weibo")
    assert status["state"] == SourceState.HEALTHY
    assert status["consecutive_failures"] == 0


def test_source_health_enters_cooldown_after_threshold():
    registry = SourceHealthRegistry(failure_threshold=3, cooldown_seconds=60)
    registry.record_failure("zhihu", "timeout")
    assert registry.should_allow_request("zhihu") is True
    assert registry.get_status("zhihu")["state"] == SourceState.DEGRADED

    registry.record_failure("zhihu", "timeout")
    assert registry.should_allow_request("zhihu") is True
    assert registry.get_status("zhihu")["state"] == SourceState.DEGRADED

    # 3rd failure trips the breaker
    registry.record_failure("zhihu", "502 Bad Gateway")
    assert registry.should_allow_request("zhihu") is False
    status = registry.get_status("zhihu")
    assert status["state"] == SourceState.COOLDOWN
    assert status["consecutive_failures"] == 3
    assert status["last_error"] == "502 Bad Gateway"


def test_source_health_probe_after_cooldown_expires():
    registry = SourceHealthRegistry(failure_threshold=2, cooldown_seconds=0.1)
    registry.record_failure("rss:bbc", "connection reset")
    registry.record_failure("rss:bbc", "connection reset")
    assert registry.should_allow_request("rss:bbc") is False

    # Wait for cooldown to expire
    time.sleep(0.12)
    # Probe request should be allowed (half-open)
    assert registry.should_allow_request("rss:bbc") is True

    # If probe succeeds, resets to healthy
    registry.record_success("rss:bbc")
    assert registry.get_status("rss:bbc")["state"] == SourceState.HEALTHY
    assert registry.get_status("rss:bbc")["consecutive_failures"] == 0
    assert registry.should_allow_request("rss:bbc") is True


def test_source_health_summary():
    registry = SourceHealthRegistry(failure_threshold=2, cooldown_seconds=60)
    registry.record_success("source_a")
    registry.record_failure("source_b", "err1")
    registry.record_failure("source_b", "err2")

    summary = registry.summary()
    assert summary["total_sources"] == 2
    assert summary["healthy_count"] == 1
    assert summary["cooldown_count"] == 1
    assert "source_a" in summary["sources"]
    assert "source_b" in summary["sources"]
