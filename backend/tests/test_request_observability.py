from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.index import RequestObservabilityMiddleware
from core.observability import obs


def test_request_middleware_adds_request_id_and_event():
    app = FastAPI()
    app.add_middleware(RequestObservabilityMiddleware)

    @app.get("/ok")
    def ok():
        return {"ok": True}

    client = TestClient(app)
    response = client.get("/ok", headers={"x-request-id": "req-test-1"})

    assert response.status_code == 200
    assert response.headers["x-request-id"] == "req-test-1"
    events = obs.snapshot()["events"]
    assert any(e["event"] == "request.completed" and e["request_id"] == "req-test-1" for e in events)


def test_stats_observability_endpoint_returns_operational_summary():
    from api.routes.stats import router
    from core.auth import require_admin

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[require_admin] = lambda: True

    client = TestClient(app)
    resp = client.get("/stats/observability")
    assert resp.status_code == 200
    data = resp.json()
    assert "requests" in data
    assert "dependencies" in data
    assert "renders" in data
    assert "cache" in data
    assert "source_health" in data
    assert "recent_failures" in data

    # Test without auth override: should return 401 or 403
    app_no_auth = FastAPI()
    app_no_auth.include_router(router)
    client_no_auth = TestClient(app_no_auth)
    resp_unauth = client_no_auth.get("/stats/observability")
    assert resp_unauth.status_code in (401, 403)
