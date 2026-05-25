from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Service(Base):
    __tablename__ = "service"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    target: Mapped[str] = mapped_column(String(512), nullable=False)
    check_type: Mapped[str] = mapped_column(String(16), nullable=False)
    keyword: Mapped[str | None] = mapped_column(String(255), nullable=True)
    tags: Mapped[str | None] = mapped_column(String(512), nullable=True)
    interval_sec: Mapped[int] = mapped_column(Integer, default=60)
    timeout_sec: Mapped[int] = mapped_column(Integer, default=10)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)

    monitor_logs: Mapped[list[MonitorLog]] = relationship(
        back_populates="service",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    alert_logs: Mapped[list[AlertLog]] = relationship(
        back_populates="service",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    maintenance_logs: Mapped[list[MaintenanceLog]] = relationship(
        back_populates="service",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class MonitorLog(Base):
    __tablename__ = "monitor_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    service_id: Mapped[int] = mapped_column(ForeignKey("service.id", ondelete="CASCADE"), index=True)
    latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    http_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    result_status: Mapped[str] = mapped_column(String(16), nullable=False)
    is_success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    error_msg: Mapped[str | None] = mapped_column(Text, nullable=True)
    checked_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, index=True)

    service: Mapped[Service] = relationship(back_populates="monitor_logs")


class AlertLog(Base):
    __tablename__ = "alert_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    service_id: Mapped[int] = mapped_column(ForeignKey("service.id", ondelete="CASCADE"), index=True)
    alert_type: Mapped[str] = mapped_column(String(16), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    first_occur_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    last_occur_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    recovered_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    alert_status: Mapped[str] = mapped_column(String(16), default="active")

    service: Mapped[Service] = relationship(back_populates="alert_logs")


class AdminUser(Base):
    __tablename__ = "admin_user"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    admin_username: Mapped[str] = mapped_column(String(64), nullable=False)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    target_type: Mapped[str] = mapped_column(String(64), nullable=False)
    target_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, index=True)


class MaintenanceLog(Base):
    __tablename__ = "maintenance_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    service_id: Mapped[int] = mapped_column(ForeignKey("service.id", ondelete="CASCADE"), index=True)
    admin_username: Mapped[str] = mapped_column(String(64), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, index=True)

    service: Mapped[Service] = relationship(back_populates="maintenance_logs")


