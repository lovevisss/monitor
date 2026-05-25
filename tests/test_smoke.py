from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from app.alerting import ALERT_COOLDOWN_SECONDS
from app.main import app


def test_health() -> None:
    with TestClient(app) as client:
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


def test_alert_cooldown_policy() -> None:
    assert ALERT_COOLDOWN_SECONDS == 6 * 3600


def test_service_crud_and_run_once() -> None:
    with TestClient(app) as client:
        login_resp = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
        assert login_resp.status_code == 200
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        payload = {
            "name": f"tcp-local-check-{uuid.uuid4().hex[:8]}",
            "target": "127.0.0.1:1",
            "check_type": "tcp",
            "tags": "核心,网络",
            "interval_sec": 60,
            "timeout_sec": 1,
            "enabled": True,
        }
        create_resp = client.post("/api/services", json=payload, headers=headers)
        assert create_resp.status_code == 200
        service_id = create_resp.json()["id"]

        ping_payload = {
            "name": f"ping-local-check-{uuid.uuid4().hex[:8]}",
            "target": "127.0.0.1",
            "check_type": "ping",
            "interval_sec": 60,
            "timeout_sec": 2,
            "enabled": False,
        }
        ping_create_resp = client.post("/api/services", json=ping_payload, headers=headers)
        assert ping_create_resp.status_code == 200
        ping_id = ping_create_resp.json()["id"]

        route_payload = {
            "name": f"zufe-route-check-{uuid.uuid4().hex[:8]}",
            "target": "www.zufe.edu.cn",
            "check_type": "zufe_route",
            "interval_sec": 60,
            "timeout_sec": 5,
            "enabled": False,
        }
        route_create_resp = client.post("/api/services", json=route_payload, headers=headers)
        assert route_create_resp.status_code == 200
        route_id = route_create_resp.json()["id"]

        run_resp = client.post(f"/api/services/{service_id}/run-now", headers=headers)
        assert run_resp.status_code == 200
        assert "is_success" in run_resp.json()

        run_all_resp = client.post("/api/services/run-all-now", headers=headers)
        assert run_all_resp.status_code == 200
        assert "processed" in run_all_resp.json()

        update_resp = client.put(
            f"/api/services/{service_id}",
            json={"interval_sec": 120},
            headers=headers,
        )
        assert update_resp.status_code == 200
        assert update_resp.json()["interval_sec"] == 120

        list_resp = client.get("/api/services")
        assert list_resp.status_code == 200
        assert any(item["id"] == service_id for item in list_resp.json())

        tag_filter_resp = client.get("/api/services", params={"tag": "核心"})
        assert tag_filter_resp.status_code == 200
        assert any(item["id"] == service_id for item in tag_filter_resp.json())

        logs_resp = client.get("/api/monitor/logs")
        assert logs_resp.status_code == 200

        overview_resp = client.get("/api/dashboard/overview")
        assert overview_resp.status_code == 200
        assert "service_total" in overview_resp.json()

        status_resp = client.get("/api/dashboard/service-status")
        assert status_resp.status_code == 200
        assert isinstance(status_resp.json(), list)

        audit_resp = client.get("/api/audit-logs", headers=headers)
        assert audit_resp.status_code == 200
        assert isinstance(audit_resp.json(), list)

        test_alert_resp = client.post("/api/alerts/test", headers=headers)
        assert test_alert_resp.status_code == 200
        assert test_alert_resp.json()["sent"] is True

        settings_resp = client.get("/api/settings", headers=headers)
        assert settings_resp.status_code == 200
        assert "database_url" in settings_resp.json()

        maintenance_create_resp = client.post(
            "/api/maintenance-logs",
            json={"service_id": service_id, "content": "重启应用服务并检查日志"},
            headers=headers,
        )
        assert maintenance_create_resp.status_code == 200
        assert maintenance_create_resp.json()["service_id"] == service_id

        maintenance_list_resp = client.get("/api/maintenance-logs", params={"service_id": service_id}, headers=headers)
        assert maintenance_list_resp.status_code == 200
        assert len(maintenance_list_resp.json()) >= 1

        save_settings_resp = client.put(
            "/api/settings",
            json={"default_interval_seconds": 60},
            headers=headers,
        )
        assert save_settings_resp.status_code == 200
        assert save_settings_resp.json()["default_interval_seconds"] == 60

        delete_resp = client.delete(f"/api/services/{service_id}", headers=headers)
        assert delete_resp.status_code == 200
        assert delete_resp.json()["deleted"] is True

        ping_delete_resp = client.delete(f"/api/services/{ping_id}", headers=headers)
        assert ping_delete_resp.status_code == 200
        assert ping_delete_resp.json()["deleted"] is True

        route_delete_resp = client.delete(f"/api/services/{route_id}", headers=headers)
        assert route_delete_resp.status_code == 200
        assert route_delete_resp.json()["deleted"] is True


