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


def test_request_metrics_quantiles_and_aggregations():
    obs = Observability()
    # Emit 10 requests with varying durations and statuses
    durations = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0]
    for i, d in enumerate(durations):
        status = 200 if i < 8 else (404 if i == 8 else 500)
        route = "/api/render" if i % 2 == 0 else "/api/device/state"
        obs.emit("request.completed", {
            "method": "GET",
            "route": route,
            "status": status,
            "duration_ms": d,
        })

    metrics = obs.request_metrics()
    assert metrics["total"] == 10
    assert metrics["successes"] == 8
    assert metrics["client_errors"] == 1
    assert metrics["server_errors"] == 1
    assert metrics["avg_duration_ms"] == 55.0
    assert metrics["p50_duration_ms"] == 55.0
    assert metrics["p95_duration_ms"] == 95.5
    assert metrics["p99_duration_ms"] == 99.1
    assert "/api/render" in metrics["by_route"]
    assert metrics["by_route"]["/api/render"]["count"] == 5


def test_render_and_cache_metrics_aggregations():
    obs = Observability()
    # Cache results
    obs.emit("cache.result", {"result": "memory", "operation": "content.get"})
    obs.emit("cache.result", {"result": "persistent", "operation": "content.get"})
    obs.emit("cache.result", {"result": "miss", "operation": "content.get"})
    obs.emit("cache.result", {"result": "expired", "operation": "content.get"})

    cache = obs.cache_metrics()
    assert cache["total"] == 4
    assert cache["memory_hits"] == 1
    assert cache["persistent_hits"] == 1
    assert cache["misses"] == 1
    assert cache["expired"] == 1
    assert cache["hit_rate"] == 0.5

    # Render results
    obs.emit("render.completed", {"mode": "WEATHER", "cache_hit": True, "duration_ms": 15.0, "fallback": False})
    obs.emit("render.completed", {"mode": "WEATHER", "cache_hit": False, "duration_ms": 80.0, "fallback": False})
    obs.emit("render.completed", {"mode": "HOTLIST", "cache_hit": False, "duration_ms": 120.0, "fallback": True})

    renders = obs.render_metrics()
    assert renders["total"] == 3
    assert renders["cache_hits"] == 1
    assert renders["fallbacks"] == 1
    assert renders["avg_duration_ms"] == 71.67
    assert renders["by_mode"]["WEATHER"]["count"] == 2
    assert renders["by_mode"]["WEATHER"]["cache_hits"] == 1
    assert renders["by_mode"]["HOTLIST"]["fallbacks"] == 1


def test_operational_summary_structure():
    obs = Observability()
    obs.emit("request.completed", {"method": "GET", "route": "/health", "status": 200, "duration_ms": 1.2})
    obs.emit("dependency.completed", {"operation": "http.get", "url_host": "api.test", "status": 200, "duration_ms": 25.0})
    obs.emit("cache.result", {"result": "memory", "operation": "content.get"})
    obs.emit("render.completed", {"mode": "DAILY", "cache_hit": True, "duration_ms": 10.0, "fallback": False})

    summary = obs.operational_summary()
    assert "requests" in summary
    assert "dependencies" in summary
    assert "renders" in summary
    assert "cache" in summary
    assert "source_health" in summary
    assert "recent_failures" in summary
    assert summary["requests"]["total"] == 1
    assert summary["dependencies"]["total"] == 1
    assert summary["renders"]["total"] == 1
    assert summary["cache"]["total"] == 1
