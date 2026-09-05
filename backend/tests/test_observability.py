from __future__ import annotations

from core.observability import Observability, get_request_id


def test_emit_records_structured_event_and_snapshot():
    obs = Observability()
    obs.emit("dependency.completed", {"operation": "rss", "status": 200, "api_key": "secret"})
    event = obs.snapshot()["events"][-1]
    assert event["event"] == "dependency.completed"
    assert event["api_key"] == "[REDACTED]"


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
