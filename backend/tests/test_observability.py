from __future__ import annotations

from core.observability import Observability, get_request_id


def test_emit_records_structured_event_and_snapshot():
    obs = Observability()
    obs.emit("dependency.completed", {"operation": "rss", "status": 200, "api_key": "secret"})
    event = obs.snapshot()["events"][-1]
    assert event["event"] == "dependency.completed"
    assert event["api_key"] == "[REDACTED]"


def test_snapshot_includes_dependency_metrics_aggregated_by_host():
    obs = Observability()
    obs.emit("dependency.completed", {"operation": "http.get", "url_host": "feed.example", "status": 200, "duration_ms": 12.5})
    obs.emit("dependency.failed", {"operation": "http.get", "url_host": "feed.example", "error_type": "TimeoutError", "duration_ms": 20.0})

    metrics = obs.snapshot()["dependency_metrics"]
    assert metrics["total"] == 2
    assert metrics["successes"] == 1
    assert metrics["failures"] == 1
    assert metrics["by_host"]["feed.example"]["count"] == 2
    assert metrics["by_host"]["feed.example"]["failures"] == 1
    assert metrics["by_host"]["feed.example"]["avg_duration_ms"] == 16.25


def test_request_context_propagates_and_restores_request_id():
    obs = Observability()
    assert get_request_id() is None
    with obs.start_request("req-123"):
        assert get_request_id() == "req-123"
    assert get_request_id() is None


def test_observation_failure_does_not_raise():
    obs = Observability(max_events=1)
    obs.emit("one", {})
    obs.emit("two", {"token": "secret"})
    assert len(obs.snapshot()["events"]) == 1
