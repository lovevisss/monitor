from __future__ import annotations

import smtplib
from datetime import datetime
from email.message import EmailMessage

import requests
from sqlalchemy import and_, desc
from sqlalchemy.orm import Session

from app.config_store import get_settings
from app.models import AlertLog, Service


ALERT_COOLDOWN_SECONDS = 6 * 3600


def _load_alert_settings() -> dict[str, object]:
    settings = get_settings()
    smtp_user = settings.alert_email_user.strip()
    return {
        "wechat_webhook": settings.alert_webhook_wechat.strip(),
        "dingtalk_webhook": settings.alert_webhook_dingtalk.strip(),
        "email_enabled": settings.alert_email_enabled,
        "email_smtp_host": settings.alert_email_host.strip(),
        "email_smtp_port": settings.alert_email_port,
        "email_smtp_user": smtp_user,
        "email_smtp_password": settings.alert_email_password.strip(),
        "email_from": settings.alert_email_from.strip() or smtp_user,
        "email_to": [item.strip() for item in settings.alert_email_to if item.strip()],
        "email_use_tls": settings.alert_email_use_tls,
    }


def should_send_down_alert(db: Session, service_id: int, now: datetime) -> bool:
    active = (
        db.query(AlertLog)
        .filter(and_(AlertLog.service_id == service_id, AlertLog.alert_type == "down", AlertLog.alert_status == "active"))
        .order_by(desc(AlertLog.last_occur_at))
        .first()
    )
    if not active:
        return True
    elapsed = (now - active.last_occur_at).total_seconds()
    return elapsed >= ALERT_COOLDOWN_SECONDS


def create_down_alert(db: Session, service: Service, reason: str, now: datetime) -> AlertLog:
    active = (
        db.query(AlertLog)
        .filter(and_(AlertLog.service_id == service.id, AlertLog.alert_type == "down", AlertLog.alert_status == "active"))
        .order_by(desc(AlertLog.last_occur_at))
        .first()
    )
    if active:
        active.last_occur_at = now
        active.reason = reason
        db.commit()
        db.refresh(active)
        return active

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
    active_down_list = (
        db.query(AlertLog)
        .filter(and_(AlertLog.service_id == service.id, AlertLog.alert_type == "down", AlertLog.alert_status == "active"))
        .order_by(desc(AlertLog.last_occur_at))
        .all()
    )
    if not active_down_list:
        return None

    for item in active_down_list:
        item.alert_status = "closed"
        item.recovered_at = now
        item.last_occur_at = now

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
    config = _load_alert_settings()
    text = (
        "[校园监控告警]"
        f"\n类型: {alert.alert_type}"
        f"\n服务: {service.name}"
        f"\n目标: {service.target}"
        f"\n原因: {alert.reason}"
        f"\n时间: {alert.last_occur_at.isoformat()}"
    )

    if config["wechat_webhook"]:
        _send_wechat(str(config["wechat_webhook"]), text)
    if config["dingtalk_webhook"]:
        _send_dingtalk(str(config["dingtalk_webhook"]), text)
    if bool(config["email_enabled"]):
        _send_email(
            subject=f"[CampusMonitor] {alert.alert_type} - {service.name}",
            body=text,
            smtp_host=str(config["email_smtp_host"]),
            smtp_port=int(config["email_smtp_port"]),
            smtp_user=str(config["email_smtp_user"]),
            smtp_password=str(config["email_smtp_password"]),
            email_from=str(config["email_from"]),
            email_to=list(config["email_to"]),
            email_use_tls=bool(config["email_use_tls"]),
        )

    print(f"[ALERT] type={alert.alert_type} service={service.name} reason={alert.reason}")


def _send_wechat(webhook: str, text: str) -> None:
    try:
        requests.post(
            webhook,
            json={"msgtype": "text", "text": {"content": text}},
            timeout=5,
        ).raise_for_status()
    except Exception as exc:
        print(f"[ALERT][WECHAT] send failed: {exc}")


def _send_dingtalk(webhook: str, text: str) -> None:
    try:
        requests.post(
            webhook,
            json={"msgtype": "text", "text": {"content": text}},
            timeout=5,
        ).raise_for_status()
    except Exception as exc:
        print(f"[ALERT][DINGTALK] send failed: {exc}")


def _send_email(
    subject: str,
    body: str,
    smtp_host: str,
    smtp_port: int,
    smtp_user: str,
    smtp_password: str,
    email_from: str,
    email_to: list[str],
    email_use_tls: bool,
) -> None:
    if not (smtp_host and email_from and email_to):
        print("[ALERT][EMAIL] missing email config, skip")
        return

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = email_from
    msg["To"] = ", ".join(email_to)
    msg.set_content(body)

    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=8) as server:
            if email_use_tls:
                server.starttls()
            if smtp_user:
                server.login(smtp_user, smtp_password)
            server.send_message(msg)
    except Exception as exc:
        print(f"[ALERT][EMAIL] send failed: {exc}")


