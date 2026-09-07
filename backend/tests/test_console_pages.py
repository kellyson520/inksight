import pytest
from fastapi.testclient import TestClient
from api.index import app


def test_console_and_static_assets_serve_correctly():
    client = TestClient(app)

    # Test root and /console landing page
    resp_root = client.get("/")
    assert resp_root.status_code == 200
    assert "text/html" in resp_root.headers.get("content-type", "")
    assert "System Pulse & Observability" in resp_root.text
    assert "reqLatency" in resp_root.text
    assert "sourceTable" in resp_root.text

    resp_console = client.get("/console")
    assert resp_console.status_code == 200
    assert "text/html" in resp_console.headers.get("content-type", "")
    assert "System Pulse & Observability" in resp_console.text
    assert "sourceTable" in resp_console.text

    # Test static assets
    resp_js = client.get("/static/console/console.js")
    assert resp_js.status_code == 200
    assert "javascript" in resp_js.headers.get("content-type", "")
    assert "observability" in resp_js.text

    resp_js_head = client.head("/static/console/console.js")
    assert resp_js_head.status_code == 200

    resp_css = client.get("/static/console/console.css")
    assert resp_css.status_code == 200
    assert "css" in resp_css.headers.get("content-type", "")
    assert ".mini-metrics.quad" in resp_css.text

    resp_css_head = client.head("/static/console/console.css")
    assert resp_css_head.status_code == 200
