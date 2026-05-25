from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ServiceBase(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    target: str = Field(min_length=1, max_length=512)
    check_type: str = Field(pattern="^(http|tcp|ping|zufe_route)$")
    keyword: str | None = None
    tags: str | None = Field(default=None, max_length=512)
    interval_sec: int = Field(default=60, ge=10, le=3600)
    timeout_sec: int = Field(default=10, ge=1, le=120)
    enabled: bool = True


class ServiceCreate(ServiceBase):
    pass


class ServiceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    target: str | None = Field(default=None, min_length=1, max_length=512)
    check_type: str | None = Field(default=None, pattern="^(http|tcp|ping|zufe_route)$")
    keyword: str | None = None
    tags: str | None = Field(default=None, max_length=512)
    interval_sec: int | None = Field(default=None, ge=10, le=3600)
    timeout_sec: int | None = Field(default=None, ge=1, le=120)
    enabled: bool | None = None


class ServiceOut(ServiceBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MonitorLogOut(BaseModel):
    id: int
    service_id: int
    latency_ms: float | None
    http_code: int | None
    result_status: str
    is_success: bool
    error_msg: str | None
    checked_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AlertLogOut(BaseModel):
    id: int
    service_id: int
    alert_type: str
    reason: str
    first_occur_at: datetime
    last_occur_at: datetime
    recovered_at: datetime | None
    alert_status: str

    model_config = ConfigDict(from_attributes=True)


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ChangePasswordRequest(BaseModel):
    old_password: str = Field(min_length=6, max_length=128)
    new_password: str = Field(min_length=6, max_length=128)


class AuditLogOut(BaseModel):
    id: int
    admin_username: str
    action: str
    target_type: str
    target_id: str | None
    detail: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RuntimeSettingsOut(BaseModel):
    database_url: str
    jwt_secret_key: str
    jwt_expire_minutes: int
    admin_username: str
    admin_password: str
    default_interval_seconds: int
    default_timeout_seconds: int
    alert_webhook_wechat: str
    alert_webhook_dingtalk: str
    alert_email_enabled: bool
    alert_email_host: str
    alert_email_port: int
    alert_email_user: str
    alert_email_password: str
    alert_email_from: str
    alert_email_to: list[str]
    alert_email_use_tls: bool


class RuntimeSettingsUpdate(BaseModel):
    database_url: str | None = None
    jwt_secret_key: str | None = None
    jwt_expire_minutes: int | None = Field(default=None, ge=5, le=10080)
    admin_username: str | None = Field(default=None, min_length=1, max_length=64)
    admin_password: str | None = Field(default=None, min_length=6, max_length=128)
    default_interval_seconds: int | None = Field(default=None, ge=10, le=3600)
    default_timeout_seconds: int | None = Field(default=None, ge=1, le=120)
    alert_webhook_wechat: str | None = None
    alert_webhook_dingtalk: str | None = None
    alert_email_enabled: bool | None = None
    alert_email_host: str | None = None
    alert_email_port: int | None = Field(default=None, ge=1, le=65535)
    alert_email_user: str | None = None
    alert_email_password: str | None = None
    alert_email_from: str | None = None
    alert_email_to: list[str] | None = None
    alert_email_use_tls: bool | None = None


class MaintenanceLogCreate(BaseModel):
    service_id: int
    content: str = Field(min_length=1, max_length=4000)


class MaintenanceLogOut(BaseModel):
    id: int
    service_id: int
    admin_username: str
    content: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)




