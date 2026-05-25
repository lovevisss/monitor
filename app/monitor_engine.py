from __future__ import annotations

from collections import defaultdict
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.orm import Session

from app.alerting import create_down_alert, create_recovered_alert, emit_notification, should_send_down_alert
from app.checkers import CheckResult, http_check, ping_check, tcp_check, zufe_route_check
from app.database import SessionLocal
from app.models import MonitorLog, Service


FAILURE_THRESHOLD = 3


class MonitorEngine:
    def __init__(self) -> None:
        self.scheduler = BackgroundScheduler(timezone="Asia/Shanghai")
        self.failure_counts: dict[int, int] = defaultdict(int)

    def start(self) -> None:
        self.scheduler.start()
        self.reload_jobs()

    def shutdown(self) -> None:
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)

    def reload_jobs(self) -> None:
        self.scheduler.remove_all_jobs()
        with SessionLocal() as db:
            services = db.query(Service).filter(Service.enabled.is_(True)).all()
            for service in services:
                self.scheduler.add_job(
                    self.run_once,
                    trigger=IntervalTrigger(seconds=service.interval_sec),
                    args=[service.id],
                    id=f"service-{service.id}",
                    replace_existing=True,
                )

    def run_once(self, service_id: int) -> CheckResult | None:
        with SessionLocal() as db:
            service = db.get(Service, service_id)
            if not service or not service.enabled:
                return None

            result = self._check_service(service)
            self._save_monitor_log(db, service, result)
            self._handle_alerts(db, service, result)
            return result

    @staticmethod
    def _check_service(service: Service) -> CheckResult:
        if service.check_type == "http":
            return http_check(service.target, service.timeout_sec, service.keyword)
        if service.check_type == "ping":
            return ping_check(service.target, service.timeout_sec)
        if service.check_type == "zufe_route":
            return zufe_route_check(service.target, service.timeout_sec)
        return tcp_check(service.target, service.timeout_sec)

    def run_all_enabled(self) -> dict[str, int]:
        processed = 0
        success = 0
        failed = 0
        with SessionLocal() as db:
            services = db.query(Service).filter(Service.enabled.is_(True)).all()
            for service in services:
                result = self.run_once(service.id)
                if result is None:
                    continue
                processed += 1
                if result.is_success:
                    success += 1
                else:
                    failed += 1
        return {"processed": processed, "success": success, "failed": failed}

    @staticmethod
    def _save_monitor_log(db: Session, service: Service, result: CheckResult) -> None:
        log = MonitorLog(
            service_id=service.id,
            latency_ms=result.latency_ms,
            http_code=result.http_code,
            result_status=result.status,
            is_success=result.is_success,
            error_msg=result.error_msg,
            checked_at=datetime.now(),
        )
        db.add(log)
        db.commit()

    def _handle_alerts(self, db: Session, service: Service, result: CheckResult) -> None:
        now = datetime.now()

        if result.is_success:
            self.failure_counts[service.id] = 0
            recovered = create_recovered_alert(db, service, now)
            if recovered:
                emit_notification(recovered, service)
            return

        self.failure_counts[service.id] += 1
        if self.failure_counts[service.id] < FAILURE_THRESHOLD:
            return

        if should_send_down_alert(db, service.id, now):
            down = create_down_alert(db, service, result.error_msg or result.status, now)
            emit_notification(down, service)


