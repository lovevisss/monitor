from __future__ import annotations

from collections import Counter
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.audit import write_audit_log
from app.config_store import get_settings, update_settings
from app.database import SessionLocal, get_db, init_db
from app.alerting import emit_notification
from app.models import AdminUser, AlertLog, AuditLog, MaintenanceLog, MonitorLog, Service
from app.monitor_engine import MonitorEngine
from app.schemas import (
    AlertLogOut,
    AuditLogOut,
    ChangePasswordRequest,
    LoginRequest,
    MaintenanceLogCreate,
    MaintenanceLogOut,
    MonitorLogOut,
    RuntimeSettingsOut,
    RuntimeSettingsUpdate,
    ServiceCreate,
    ServiceOut,
    ServiceUpdate,
    TokenOut,
)
from app.security import authenticate_admin, create_access_token, ensure_default_admin, get_current_admin, hash_password, verify_password


engine = MonitorEngine()
PROJECT_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist"


def _normalize_tags(raw: str | None) -> str | None:
    if raw is None:
        return None
    parts = [item.strip() for item in raw.replace(";", ",").split(",") if item.strip()]
    if not parts:
        return None
    unique = list(dict.fromkeys(parts))
    return ",".join(unique)


def _has_tag(raw_tags: str | None, tag: str) -> bool:
    if not raw_tags:
        return False
    wanted = tag.strip()
    if not wanted:
        return True
    return wanted in [item.strip() for item in raw_tags.split(",") if item.strip()]


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    with SessionLocal() as db:
        ensure_default_admin(db)
    engine.start()
    try:
        yield
    finally:
        engine.shutdown()


app = FastAPI(title="Campus Service Monitor", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if (FRONTEND_DIST / "assets").exists():
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIST / "assets")), name="frontend-assets")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/")
def frontend_home():
    index_html = FRONTEND_DIST / "index.html"
    if index_html.exists():
        return FileResponse(index_html)
    return JSONResponse(
        status_code=503,
        content={
            "message": "frontend not built yet",
            "hint": "run: Set-Location frontend; npm install; npm run build",
        },
    )


@app.get("/api/services", response_model=list[ServiceOut])
def list_services(db: Session = Depends(get_db), tag: str | None = Query(default=None)):
    services = db.query(Service).order_by(Service.id.desc()).all()
    if tag:
        services = [item for item in services if _has_tag(item.tags, tag)]
    return services


@app.post("/api/auth/login", response_model=TokenOut)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    admin = authenticate_admin(db, payload.username, payload.password)
    if not admin:
        raise HTTPException(status_code=401, detail="invalid username or password")

    token = create_access_token(admin.username)
    return TokenOut(access_token=token)


@app.post("/api/auth/change-password")
def change_password(
    payload: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
):
    if not verify_password(payload.old_password, current_admin.password_hash):
        raise HTTPException(status_code=400, detail="old password is incorrect")

    current_admin.password_hash = hash_password(payload.new_password)
    db.commit()
    write_audit_log(
        db,
        current_admin,
        action="change_password",
        target_type="admin_user",
        target_id=str(current_admin.id),
        detail="admin changed own password",
    )
    return {"changed": True}


@app.get("/api/auth/me")
def auth_me(current_admin: AdminUser = Depends(get_current_admin)):
    return {"username": current_admin.username, "is_active": current_admin.is_active}


@app.post("/api/services", response_model=ServiceOut)
def create_service(
    payload: ServiceCreate,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
):
    exists = db.query(Service).filter(Service.name == payload.name).first()
    if exists:
        raise HTTPException(status_code=409, detail="service name already exists")

    data = payload.model_dump()
    data["tags"] = _normalize_tags(data.get("tags"))
    service = Service(**data)
    db.add(service)
    db.commit()
    db.refresh(service)
    write_audit_log(
        db,
        current_admin,
        action="create_service",
        target_type="service",
        target_id=str(service.id),
        detail=f"name={service.name}",
    )
    engine.reload_jobs()
    return service


@app.put("/api/services/{service_id}", response_model=ServiceOut)
def update_service(
    service_id: int,
    payload: ServiceUpdate,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
):
    service = db.get(Service, service_id)
    if not service:
        raise HTTPException(status_code=404, detail="service not found")

    update_data = payload.model_dump(exclude_unset=True)
    if "tags" in update_data:
        update_data["tags"] = _normalize_tags(update_data.get("tags"))

    for key, value in update_data.items():
        setattr(service, key, value)

    db.commit()
    db.refresh(service)
    write_audit_log(
        db,
        current_admin,
        action="update_service",
        target_type="service",
        target_id=str(service.id),
        detail=f"name={service.name}",
    )
    engine.reload_jobs()
    return service


@app.delete("/api/services/{service_id}")
def delete_service(
    service_id: int,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
):
    service = db.get(Service, service_id)
    if not service:
        raise HTTPException(status_code=404, detail="service not found")

    service_name = service.name
    db.delete(service)
    db.commit()
    write_audit_log(
        db,
        current_admin,
        action="delete_service",
        target_type="service",
        target_id=str(service_id),
        detail=f"name={service_name}",
    )
    engine.reload_jobs()
    return {"deleted": True}


@app.post("/api/services/{service_id}/run-now")
def run_service_once(
    service_id: int,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
):
    result = engine.run_once(service_id)
    if result is None:
        raise HTTPException(status_code=404, detail="service not found or disabled")
    write_audit_log(
        db,
        current_admin,
        action="run_service_once",
        target_type="service",
        target_id=str(service_id),
        detail="manual check triggered",
    )
    return result.__dict__


@app.get("/api/monitor/logs", response_model=list[MonitorLogOut])
def list_monitor_logs(
    db: Session = Depends(get_db),
    service_id: int | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
):
    query = db.query(MonitorLog)
    if service_id is not None:
        query = query.filter(MonitorLog.service_id == service_id)
    return query.order_by(desc(MonitorLog.checked_at)).limit(limit).all()


@app.get("/api/alerts", response_model=list[AlertLogOut])
def list_alerts(
    db: Session = Depends(get_db),
    service_id: int | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
):
    query = db.query(AlertLog)
    if service_id is not None:
        query = query.filter(AlertLog.service_id == service_id)
    return query.order_by(desc(AlertLog.first_occur_at)).limit(limit).all()


@app.post("/api/alerts/test")
def send_test_alert(
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
):
    service = db.query(Service).order_by(Service.id.asc()).first()
    if not service:
        raise HTTPException(status_code=400, detail="no service found, create one first")

    now = datetime.now()
    test_alert = AlertLog(
        service_id=service.id,
        alert_type="test",
        reason=f"manual test alert by {current_admin.username}",
        first_occur_at=now,
        last_occur_at=now,
        recovered_at=None,
        alert_status="closed",
    )
    db.add(test_alert)
    db.commit()
    db.refresh(test_alert)

    emit_notification(test_alert, service)
    write_audit_log(
        db,
        current_admin,
        action="send_test_alert",
        target_type="alert_channel",
        target_id=str(test_alert.id),
        detail=f"service_id={service.id}",
    )
    return {"sent": True, "service_id": service.id, "alert_id": test_alert.id}


@app.get("/api/maintenance-logs", response_model=list[MaintenanceLogOut])
def list_maintenance_logs(
    db: Session = Depends(get_db),
    service_id: int | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    current_admin: AdminUser = Depends(get_current_admin),
):
    _ = current_admin
    query = db.query(MaintenanceLog)
    if service_id is not None:
        query = query.filter(MaintenanceLog.service_id == service_id)
    return query.order_by(desc(MaintenanceLog.created_at)).limit(limit).all()


@app.post("/api/maintenance-logs", response_model=MaintenanceLogOut)
def create_maintenance_log(
    payload: MaintenanceLogCreate,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
):
    service = db.get(Service, payload.service_id)
    if not service:
        raise HTTPException(status_code=404, detail="service not found")

    item = MaintenanceLog(
        service_id=payload.service_id,
        admin_username=current_admin.username,
        content=payload.content,
    )
    db.add(item)
    db.commit()
    db.refresh(item)

    write_audit_log(
        db,
        current_admin,
        action="create_maintenance_log",
        target_type="service",
        target_id=str(payload.service_id),
        detail=payload.content[:120],
    )
    return item


@app.get("/api/audit-logs", response_model=list[AuditLogOut])
def list_audit_logs(
    db: Session = Depends(get_db),
    limit: int = Query(default=100, ge=1, le=500),
    current_admin: AdminUser = Depends(get_current_admin),
):
    _ = current_admin
    return db.query(AuditLog).order_by(desc(AuditLog.created_at)).limit(limit).all()


@app.get("/api/settings", response_model=RuntimeSettingsOut)
def get_runtime_settings(current_admin: AdminUser = Depends(get_current_admin)):
    _ = current_admin
    settings = get_settings()
    return RuntimeSettingsOut(**settings.model_dump())


@app.put("/api/settings", response_model=RuntimeSettingsOut)
def save_runtime_settings(
    payload: RuntimeSettingsUpdate,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
):
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        return RuntimeSettingsOut(**get_settings().model_dump())

    settings = update_settings(updates)
    write_audit_log(
        db,
        current_admin,
        action="update_settings",
        target_type="runtime_settings",
        detail=", ".join(sorted(updates.keys())),
    )
    return RuntimeSettingsOut(**settings.model_dump())


@app.get("/api/dashboard/overview")
def dashboard_overview(db: Session = Depends(get_db)):
    services = db.query(Service).all()
    logs = db.query(MonitorLog).order_by(desc(MonitorLog.checked_at)).limit(2000).all()
    status_counter = Counter(log.result_status for log in logs)
    avg_latency = [log.latency_ms for log in logs if log.latency_ms is not None]

    online_count = sum(1 for s in services if s.enabled)
    return {
        "service_total": len(services),
        "service_enabled": online_count,
        "avg_latency_ms": round(sum(avg_latency) / len(avg_latency), 2) if avg_latency else None,
        "status_distribution": dict(status_counter),
        "log_count": len(logs),
    }


@app.get("/api/dashboard/service-status")
def dashboard_service_status(db: Session = Depends(get_db)):
    services = db.query(Service).order_by(Service.id.asc()).all()
    logs = db.query(MonitorLog).order_by(desc(MonitorLog.checked_at)).limit(5000).all()

    latest_by_service: dict[int, MonitorLog] = {}
    for log in logs:
        if log.service_id not in latest_by_service:
            latest_by_service[log.service_id] = log

    items = []
    for service in services:
        latest = latest_by_service.get(service.id)
        items.append(
            {
                "service_id": service.id,
                "name": service.name,
                "check_type": service.check_type,
                "target": service.target,
                "keyword": service.keyword,
                "tags": service.tags,
                "interval_sec": service.interval_sec,
                "timeout_sec": service.timeout_sec,
                "enabled": service.enabled,
                "latest_status": latest.result_status if latest else "unknown",
                "latest_checked_at": latest.checked_at.isoformat() if latest else None,
                "latest_latency_ms": latest.latency_ms if latest else None,
                "latest_http_code": latest.http_code if latest else None,
                "latest_error_msg": latest.error_msg if latest else None,
            }
        )
    return items



