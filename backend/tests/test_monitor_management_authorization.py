from fastapi.testclient import TestClient

from api.index import app


def test_monitor_management_requires_admin_token(monkeypatch):
    monkeypatch.setenv("ADMIN_TOKEN", "monitor-admin")
    with TestClient(app) as client:
        assert client.get("/api/monitors").status_code == 403
        assert client.post("/api/monitors/check").status_code == 403
        assert client.get("/api/monitors/notices").status_code == 403


def test_monitor_management_accepts_admin_token(monkeypatch):
    monkeypatch.setenv("ADMIN_TOKEN", "monitor-admin")
    with TestClient(app) as client:
        headers = {"Authorization": "Bearer monitor-admin"}
        response = client.get("/api/monitors", headers=headers)
        assert response.status_code == 200
        assert "targets" in response.json()
