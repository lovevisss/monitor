from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from app.main import app


def test_health() -> None:
    with TestClient(app) as client:
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


def test_service_crud_and_run_once() -> None:
    with TestClient(app) as client:
        payload = {
            "name": f"tcp-local-check-{uuid.uuid4().hex[:8]}",
            "target": "127.0.0.1:1",
            "check_type": "tcp",
            "interval_sec": 60,
            "timeout_sec": 1,
            "enabled": True,
        }
        create_resp = client.post("/api/services", json=payload)
        assert create_resp.status_code == 200
        service_id = create_resp.json()["id"]

        run_resp = client.post(f"/api/services/{service_id}/run-now")
        assert run_resp.status_code == 200
        assert "is_success" in run_resp.json()

        list_resp = client.get("/api/services")
        assert list_resp.status_code == 200
        assert any(item["id"] == service_id for item in list_resp.json())

        logs_resp = client.get("/api/monitor/logs")
        assert logs_resp.status_code == 200

        overview_resp = client.get("/api/dashboard/overview")
        assert overview_resp.status_code == 200
        assert "service_total" in overview_resp.json()


