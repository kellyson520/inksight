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
