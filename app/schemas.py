from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ServiceBase(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    target: str = Field(min_length=1, max_length=512)
    check_type: str = Field(pattern="^(http|tcp)$")
    keyword: str | None = None
    interval_sec: int = Field(default=60, ge=10, le=3600)
    timeout_sec: int = Field(default=10, ge=1, le=120)
    enabled: bool = True


class ServiceCreate(ServiceBase):
    pass


class ServiceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    target: str | None = Field(default=None, min_length=1, max_length=512)
    check_type: str | None = Field(default=None, pattern="^(http|tcp)$")
    keyword: str | None = None
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




