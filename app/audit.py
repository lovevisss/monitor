from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import AdminUser, AuditLog


def write_audit_log(
    db: Session,
    admin: AdminUser,
    action: str,
    target_type: str,
    target_id: str | None = None,
    detail: str | None = None,
) -> None:
    entry = AuditLog(
        admin_username=admin.username,
        action=action,
        target_type=target_type,
        target_id=target_id,
        detail=detail,
    )
    db.add(entry)
    db.commit()

