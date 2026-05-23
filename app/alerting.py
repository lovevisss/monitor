from __future__ import annotations

from datetime import datetime

from sqlalchemy import and_, desc
from sqlalchemy.orm import Session

from app.models import AlertLog, Service


ALERT_COOLDOWN_SECONDS = 300


def should_send_down_alert(db: Session, service_id: int, now: datetime) -> bool:
    latest = (
        db.query(AlertLog)
        .filter(and_(AlertLog.service_id == service_id, AlertLog.alert_type == "down"))
        .order_by(desc(AlertLog.last_occur_at))
        .first()
    )
    if not latest:
        return True
    elapsed = (now - latest.last_occur_at).total_seconds()
    return elapsed >= ALERT_COOLDOWN_SECONDS


def create_down_alert(db: Session, service: Service, reason: str, now: datetime) -> AlertLog:
    alert = AlertLog(
        service_id=service.id,
        alert_type="down",
        reason=reason,
        first_occur_at=now,
        last_occur_at=now,
        alert_status="active",
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return alert


def create_recovered_alert(db: Session, service: Service, now: datetime) -> AlertLog | None:
    active_down = (
        db.query(AlertLog)
        .filter(and_(AlertLog.service_id == service.id, AlertLog.alert_type == "down", AlertLog.alert_status == "active"))
        .order_by(desc(AlertLog.last_occur_at))
        .first()
    )
    if not active_down:
        return None

    active_down.alert_status = "closed"
    active_down.recovered_at = now
    active_down.last_occur_at = now

    recovered = AlertLog(
        service_id=service.id,
        alert_type="recovered",
        reason="service recovered",
        first_occur_at=now,
        last_occur_at=now,
        recovered_at=now,
        alert_status="closed",
    )
    db.add(recovered)
    db.commit()
    db.refresh(recovered)
    return recovered


def emit_notification(alert: AlertLog, service: Service) -> None:
    # Placeholder notifier. Replace with WeCom/DingTalk/Email integration.
    print(f"[ALERT] type={alert.alert_type} service={service.name} reason={alert.reason}")

