import pytest
from starlette.applications import Starlette
from starlette.responses import JSONResponse, Response
from starlette.testclient import TestClient
from api.index import RequestObservabilityMiddleware
from core.observability import obs


def test_request_observability_middleware_captures_device_metadata():
    app = Starlette()
    app.add_middleware(RequestObservabilityMiddleware)

    @app.route("/api/device/{mac}/heartbeat", methods=["POST"])
    async def heartbeat(request):
        return JSONResponse({"ok": True})

    @app.route("/api/render", methods=["GET"])
    async def render(request):
        return Response(b"bmp", media_type="image/bmp")

    @app.route("/api/device/{mac}/state", methods=["GET"])
    async def state(request):
        return JSONResponse({"detail": "token required"}, status_code=401)

    client = TestClient(app)

    # 1. Device heartbeat
    resp1 = client.post(
        "/api/device/70:AF:09:75:51:84/heartbeat",
        headers={"User-Agent": "ESP32HTTPClient", "X-Device-Token": "test-token-123"},
    )
    assert resp1.status_code == 200
    ev1 = [e for e in obs._events if e.get("event") == "request.completed"][-1]
    assert ev1.get("mac") == "70:AF:09:75:51:84"
    assert ev1.get("has_token") is True
    assert "ESP32" in str(ev1.get("user_agent"))

    # 2. Render query param mac
    resp2 = client.get(
        "/api/render?mac=70:AF:09:75:51:84&w=400&h=300",
        headers={"User-Agent": "ESP32HTTPClient"},
    )
    assert resp2.status_code == 200
    ev2 = [e for e in obs._events if e.get("event") == "request.completed"][-1]
    assert ev2.get("mac") == "70:AF:09:75:51:84"
    assert ev2.get("has_token") is False

    # 3. Failed device request emits device.request.failed
    resp3 = client.get(
        "/api/device/70:AF:09:75:51:84/state",
        headers={"User-Agent": "ESP32HTTPClient"},
    )
    assert resp3.status_code == 401
    ev_fail = [e for e in obs._events if e.get("event") == "device.request.failed"]
    assert len(ev_fail) > 0
    last_fail = ev_fail[-1]
    assert last_fail.get("mac") == "70:AF:09:75:51:84"
    assert last_fail.get("status") == 401


def test_access_log_filter_preserves_error_status():
    import logging
    from api.index import _AccessLogFilter

    filter_instance = _AccessLogFilter()

    # Normal 200 state polling: should be filtered out (return False)
    record_200 = logging.LogRecord(
        name="uvicorn.access",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg='%s - "%s" %d',
        args=("112.224.199.138", 'GET /api/device/70:AF:09:75:51:84/state HTTP/1.1', "/api/device/70:AF:09:75:51:84/state", 200),
        exc_info=None,
    )
    assert filter_instance.filter(record_200) is False

    # Error 401/404 state polling: should NOT be filtered out (return True)
    record_401 = logging.LogRecord(
        name="uvicorn.access",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg='%s - "%s" %d',
        args=("112.224.199.138", 'GET /api/device/70:AF:09:75:51:84/state HTTP/1.1', "/api/device/70:AF:09:75:51:84/state", 401),
        exc_info=None,
    )
    assert filter_instance.filter(record_401) is True

    record_404 = logging.LogRecord(
        name="uvicorn.access",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg='%s - "%s" %d',
        args=("112.224.199.138", 'GET /api/device/70:AF:09:75:51:84/state HTTP/1.1', "/api/device/70:AF:09:75:51:84/state", 404),
        exc_info=None,
    )
    assert filter_instance.filter(record_404) is True
