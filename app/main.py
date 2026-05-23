from __future__ import annotations

from collections import Counter
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Query
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.database import get_db, init_db
from app.models import AlertLog, MonitorLog, Service
from app.monitor_engine import MonitorEngine
from app.schemas import AlertLogOut, MonitorLogOut, ServiceCreate, ServiceOut, ServiceUpdate


engine = MonitorEngine()


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    engine.start()
    try:
        yield
    finally:
        engine.shutdown()


app = FastAPI(title="Campus Service Monitor", version="1.0.0", lifespan=lifespan)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/services", response_model=list[ServiceOut])
def list_services(db: Session = Depends(get_db)):
    return db.query(Service).order_by(Service.id.desc()).all()


@app.post("/api/services", response_model=ServiceOut)
def create_service(payload: ServiceCreate, db: Session = Depends(get_db)):
    exists = db.query(Service).filter(Service.name == payload.name).first()
    if exists:
        raise HTTPException(status_code=409, detail="service name already exists")

    service = Service(**payload.model_dump())
    db.add(service)
    db.commit()
    db.refresh(service)
    engine.reload_jobs()
    return service


@app.put("/api/services/{service_id}", response_model=ServiceOut)
def update_service(service_id: int, payload: ServiceUpdate, db: Session = Depends(get_db)):
    service = db.get(Service, service_id)
    if not service:
        raise HTTPException(status_code=404, detail="service not found")

    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(service, key, value)

    db.commit()
    db.refresh(service)
    engine.reload_jobs()
    return service


@app.delete("/api/services/{service_id}")
def delete_service(service_id: int, db: Session = Depends(get_db)):
    service = db.get(Service, service_id)
    if not service:
        raise HTTPException(status_code=404, detail="service not found")

    db.delete(service)
    db.commit()
    engine.reload_jobs()
    return {"deleted": True}


@app.post("/api/services/{service_id}/run-now")
def run_service_once(service_id: int):
    result = engine.run_once(service_id)
    if result is None:
        raise HTTPException(status_code=404, detail="service not found or disabled")
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



